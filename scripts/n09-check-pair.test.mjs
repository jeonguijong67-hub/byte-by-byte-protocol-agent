// Serialized A/B fixtures only; these tests do not run REA, TCP or a model.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { checkPair, main } from './n09-check-pair.mjs';
import { fingerprintSources } from './n09-source-state.mjs';
import { BUDGET } from './n09-contract.mjs';
import { detailBundle } from './rea-detail.mjs';

const sha = value => createHash('sha256').update(value).digest('hex');
const retained = path.resolve('runs/n09-pair-tests');
await mkdir(retained, {recursive:true});

async function fixture(dirty = false, experiment = 'practice') {
  const dir = await mkdtemp(path.join(retained, 'fixture-'));
  const rawPath = path.join(dir, 'binary.raw');
  const reaPath = path.join(dir, 'rea.json');
  const requestPath = path.join(dir, 'request.json');
  const fingerprint = await fingerprintSources();
  const binaryHash = sha('explicit mock binary');
  const pcapHash = sha('mock pcap');
  const ghidraEvidence = (operation, normalized_result) => JSON.stringify({
    evidence_id: `ev_fixture_${operation}`, operation, provider: {id:'ghidra'},
    subject: {digest:{sha256:binaryHash}}, normalized_result,
  });
  const raw = ghidraEvidence('binary_overview', {fixture:true});
  await writeFile(rawPath, raw);
  await writeFile(requestPath, JSON.stringify({messages:[{role:'system',content:'Explicit test fixture prompt.'}]}));
  await writeFile(reaPath, JSON.stringify({success:true,mode:'rea-only',execution_backend:'real',
    evidence:{raw_file:rawPath,validation:{upstream_provider:'ghidra',subject_sha256:binaryHash}}}));
  const a = {success:true,execution:'prepare',experiment,command_backend:'real',
    model_called:false,usage:{model_calls:0,server_queries:0},experiment_score:false,n09_complete:false,
    spec:null,condition:'A',budget:{...BUDGET},input:{pcap:{sha256:pcapHash}},
    evidence:[{source:'packet',text:'Explicit mock packet evidence.',raw_sha256:sha('mock packets')}],
    runtime:{code_dirty:dirty,code_commit:'a'.repeat(40),source_fingerprint:fingerprint},
    stages:[{status:'success'}],request_file:requestPath};
  if (experiment === 'E1') {
    const rawFile = path.join(dir, 'streams.json');
    const streams = JSON.stringify({format:'tcp-streams-v1',pcap_sha256:pcapHash,sessions:[]});
    await writeFile(rawFile, streams);
    a.runtime.packet_format = 'tcp-streams-v1';
    a.evidence[0] = {source:'packet',text:streams,raw_file:rawFile,raw_sha256:sha(streams)};
  }
  const b = structuredClone(a);
  b.condition = 'B'; b.input.binary = {sha256:binaryHash};
  b.runtime.rea_result_file = reaPath;
  const overview = {source:'binary',operation:'binary_overview',raw_file:rawPath,raw_sha256:sha(raw)};
  b.evidence.push(overview);
  const bundlePath = path.join(dir, 'binary.bundle.json');
  const saveBundle = async bundle => {
    const bundleRaw = JSON.stringify(bundle);
    await writeFile(bundlePath, bundleRaw);
    b.evidence[1] = {source:'binary',operation:'rea-evidence-bundle-v1',raw_file:bundlePath,raw_sha256:sha(bundleRaw)};
  };
  let bundle;
  if (experiment === 'E1') {
    bundle = await detailBundle({binaryPath:'fixture',binarySha:binaryHash,overviewPath:rawPath,artifacts:dir,
      runCommand:async () => ({exitCode:0,stdout:ghidraEvidence('search_procedures', []),stderr:''})});
    b.runtime.rea_detail_profile = structuredClone(bundle.profile);
    await saveBundle(bundle);
  }
  const aPath = path.join(dir,'A.json'), bPath = path.join(dir,'B.json'), outPath = path.join(dir,'pair.json');
  const persist = async () => {await writeFile(aPath,JSON.stringify(a));await writeFile(bPath,JSON.stringify(b));};
  await persist();
  return {a,b,aPath,bPath,outPath,overview,bundle,saveBundle,persist,run:options=>checkPair({aPath,bPath,outPath,...options})};
}

test('pair checker retains the clean-checkout default', async () => {
  const f = await fixture();
  const result = await f.run();
  assert.equal(result.code_dirty,false);
  assert.equal(result.reproducibility.reference_run_eligible,true);
  assert.equal(result.reproducibility.sources_verified,true);
});

test('clean E1 pair saves its experiment label, packet format and binary profile without scoring', async () => {
  const f = await fixture(false, 'E1');
  await f.run();
  const saved = JSON.parse(await readFile(f.outPath,'utf8'));
  assert.equal(saved.experiment,'E1');
  assert.equal(saved.packet_format,'tcp-streams-v1');
  assert.deepEqual(saved.rea_detail_profile,f.bundle.profile);
  assert.equal(saved.rea_detail_profile.selected_procedure,null);
  assert.equal(saved.model_calls,0);
  assert.equal(saved.experiment_score,false);
});

test('E1 rejects tcpdump and missing packet format in either condition', async () => {
  for (const condition of ['a','b']) {
    const f = await fixture(false, 'E1');
    f[condition].runtime.packet_format = 'tcpdump';
    await f.persist();
    const error = new RegExp(`E1 condition ${condition.toUpperCase()} requires --packet-format tcp-streams-v1`);
    await assert.rejects(f.run(), error);
    delete f[condition].runtime.packet_format;
    await f.persist();
    await assert.rejects(f.run(), error);
    await assert.rejects(readFile(f.outPath), {code:'ENOENT'});
  }
});

test('E1 checks the format and PCAP digest of the packet artifact', async () => {
  const f = await fixture(false, 'E1');
  const updatePackets = async packet => {
    const raw = JSON.stringify(packet);
    await writeFile(f.a.evidence[0].raw_file, raw);
    for (const result of [f.a, f.b]) {
      result.evidence[0].text = raw;
      result.evidence[0].raw_sha256 = sha(raw);
    }
    await f.persist();
  };
  await updatePackets({format:'tcpdump',pcap_sha256:f.a.input.pcap.sha256});
  await assert.rejects(f.run(), /requires TCP stream evidence/);
  await updatePackets({format:'tcp-streams-v1',pcap_sha256:sha('other pcap'),sessions:[]});
  await assert.rejects(f.run(), /stream evidence PCAP digest differs/);
  await assert.rejects(readFile(f.outPath), {code:'ENOENT'});
});

test('E1 rejects B with only a binary overview', async () => {
  const f = await fixture(false, 'E1');
  f.b.evidence[1] = f.overview;
  await f.persist();
  await assert.rejects(f.run(), /requires --binary-profile named-procedure-v1/);
  await assert.rejects(readFile(f.outPath), {code:'ENOENT'});
});

test('E1 requires the named profile in both the runtime and the B bundle', async () => {
  const f = await fixture(false, 'E1');
  delete f.b.runtime.rea_detail_profile;
  await f.persist();
  await assert.rejects(f.run(), /requires a recorded named-procedure-v1 profile/);
  f.b.runtime.rea_detail_profile = structuredClone(f.bundle.profile);
  f.bundle.profile.version = 'other-profile';
  await f.saveBundle(f.bundle);
  await f.persist();
  await assert.rejects(f.run(), /evidence bundle requires the named-procedure-v1 profile/);
  f.bundle.profile.version = 'named-procedure-v1';
  f.b.runtime.rea_detail_profile.selected_procedure = {address:'fixture'};
  await f.saveBundle(f.bundle);
  await f.persist();
  await assert.rejects(f.run(), /runtime profile differs from its evidence bundle/);
  await assert.rejects(readFile(f.outPath), {code:'ENOENT'});
});

test('E1 rejects the dirty override even when both preparations are clean', async () => {
  const f = await fixture(false, 'E1');
  await assert.rejects(main([f.aPath,f.bPath,f.outPath,'--allow-dirty']), /E1 does not allow/);
  await assert.rejects(readFile(f.outPath), {code:'ENOENT'});
});

test('E1 rejects a dirty preparation in either condition', async () => {
  for (const condition of ['a','b']) {
    const f = await fixture(false, 'E1');
    f[condition].runtime.code_dirty = true;
    await f.persist();
    await assert.rejects(f.run(), /E1 requires both preparations from a clean checkout/);
    await assert.rejects(readFile(f.outPath), {code:'ENOENT'});
  }
});

test('mixed practice and E1 labels cannot pass with or without the override', async () => {
  const f = await fixture();
  f.b.experiment = 'E1';
  await f.persist();
  await assert.rejects(f.run(), /A\/B experiment labels differ/);
  await assert.rejects(f.run({allowDirty:true}), /A\/B experiment labels differ/);
  await assert.rejects(readFile(f.outPath), {code:'ENOENT'});
});

test('dirty practice requires explicit opt-in before writing a success summary', async () => {
  const f = await fixture(true);
  await assert.rejects(f.run(), /Uncommitted changes/);
  await assert.rejects(readFile(f.outPath), {code:'ENOENT'});
});

test('opted-in dirty practice verifies actual sources and retains the dirty label', async () => {
  const f = await fixture(true);
  const result = await f.run({allowDirty:true});
  assert.equal(result.code_dirty,true);
  assert.equal(result.reproducibility.reference_run_eligible,false);
  assert.equal(result.reproducibility.local_practice_dirty_allowed,true);
  assert.equal(result.reproducibility.sources_verified,true);
  assert.equal(result.experiment_score,false);
});

test('dirty opt-in rejects legacy preparation without actual source hashes', async () => {
  const f = await fixture(true);
  delete f.a.runtime.source_fingerprint; delete f.b.runtime.source_fingerprint;
  await f.persist();
  await assert.rejects(f.run({allowDirty:true}), /require a recorded source fingerprint/);
});

test('dirty opt-in rejects A/B prepared from different runner sources', async () => {
  const f = await fixture(true);
  f.b.runtime.source_fingerprint.sha256 = 'b'.repeat(64);
  await f.persist();
  await assert.rejects(f.run({allowDirty:true}), /A\/B runner sources differ/);
});

test('matching but stale A/B source hashes fail against the current files', async () => {
  const f = await fixture(true);
  f.a.runtime.source_fingerprint.files[0].sha256 = 'b'.repeat(64);
  f.b.runtime.source_fingerprint = structuredClone(f.a.runtime.source_fingerprint);
  await f.persist();
  await assert.rejects(f.run({allowDirty:true}), /changed since preparation/);
});

test('dirty opt-in still rejects a working-tree status change between A and B', async () => {
  const f = await fixture(true); f.b.runtime.code_dirty = false;
  await f.persist();
  await assert.rejects(f.run({allowDirty:true}), /working-tree status differs/);
});

test('pair CLI rejects unknown flags', async () => {
  await assert.rejects(main(['A','B','out','--ignore-checks']), /Usage:/);
});
