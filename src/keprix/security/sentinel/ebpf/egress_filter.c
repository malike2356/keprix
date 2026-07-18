// sentinel/ebpf/egress_filter.c
// Documented stub: blocks outbound connections to blacklisted IPs at the kernel level.
// Not loaded by default. Load via bpftool or BCC when SENTINEL_EBPF=1 on a prepared host.
//
// Build (example, host-specific):
//   clang -O2 -g -target bpf -c egress_filter.c -o egress_filter.o
//
// This file is intentionally a stub for the MVP; do not compile into production
// images unless operators have validated the cgroup/connect4 attach path.

#include <linux/bpf.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10000);
    __type(key, __u32);    // IP address (network byte order)
    __type(value, __u8);   // 1 = blocked
} blocklist SEC(".maps");

SEC("cgroup/connect4")
int egress_filter(struct bpf_sock_addr *ctx) {
    __u32 dst_ip = ctx->user_ip4;
    __u8 *blocked = bpf_map_lookup_elem(&blocklist, &dst_ip);

    if (blocked && *blocked == 1) {
        return 0;  // Reject
    }
    return 1;  // Allow
}

char LICENSE[] SEC("license") = "GPL";
