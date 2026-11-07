/* N05 public practice fixture. Not the hidden experiment service. */
#include <arpa/inet.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int send_all(int fd, const char *message) {
    size_t sent = 0;
    size_t length = strlen(message);
    while (sent < length) {
        ssize_t count = send(fd, message + sent, length - sent, 0);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return -1;
        sent += (size_t)count;
    }
    return 0;
}

static void handle_request(int client) {
    char request[64] = {0};
    size_t used = 0;
    int complete = 0;

    /* TCP recv boundaries do not determine message boundaries. */
    while (used < sizeof(request) - 1) {
        ssize_t count = recv(client, request + used, 1, 0);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return;
        if (request[used++] == '\n') {
            complete = 1;
            break;
        }
    }

    if (complete && used == 5 && memcmp(request, "PING\n", 5) == 0) {
        (void)send_all(client, "PONG\n");
    } else {
        (void)send_all(client, "ERR\n");
    }
}

int main(int argc, char **argv) {
    long port = 19005;
    if (argc > 2) {
        fprintf(stderr, "Usage: %s [port]\n", argv[0]);
        return 2;
    }
    if (argc == 2) {
        char *end = NULL;
        errno = 0;
        port = strtol(argv[1], &end, 10);
        if (errno || end == argv[1] || *end || port < 1 || port > 65535) {
            fprintf(stderr, "Port must be an integer from 1 to 65535\n");
            return 2;
        }
    }

    signal(SIGPIPE, SIG_IGN);
    int listener = socket(AF_INET, SOCK_STREAM, 0);
    if (listener < 0) { perror("socket"); return 1; }
    int reuse = 1;
    if (setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        perror("setsockopt"); close(listener); return 1;
    }
    struct sockaddr_in address = {0};
    address.sin_family = AF_INET;
    address.sin_port = htons((unsigned short)port);
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(listener, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind"); close(listener); return 1;
    }
    if (listen(listener, 4) < 0) { perror("listen"); close(listener); return 1; }
    fprintf(stderr, "N05 practice TCP service listening on 127.0.0.1:%ld\n", port);

    for (;;) {
        int client = accept(listener, NULL, NULL);
        if (client < 0 && errno == EINTR) continue;
        if (client < 0) { perror("accept"); close(listener); return 1; }
        handle_request(client);
        close(client);
    }
}
