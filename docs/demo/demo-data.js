(function () {
  "use strict";

  const state = {
    cpu: 22,
    mem: 41,
    diskPercent: 58,
    netSent: 4_100_000_000,
    netRecv: 39_800_000_000,
    diskRead: 2_400_000_000,
    diskWrite: 7_300_000_000,
    boot: Date.now() - 1000 * 60 * 60 * 31 - 1000 * 60 * 14,
  };

  const CORES = 4;
  const TOTAL_MEM = 8 * 1024 ** 3;
  const TOTAL_DISK = 64 * 1024 ** 3;
  const TOTAL_SWAP = 2 * 1024 ** 3;

  function drift(value, step, lo, hi) {
    let next = value + (Math.random() - 0.5) * step;
    if (Math.random() < 0.06) next += (Math.random() - 0.5) * step * 6;
    return Math.min(hi, Math.max(lo, next));
  }

  let lastAdvance = Date.now();

  function advance() {
    const now = Date.now();
    const dt = Math.min(2, Math.max(0.001, (now - lastAdvance) / 1000));
    lastAdvance = now;
    state.cpu = drift(state.cpu, 9 * Math.sqrt(dt), 2, 96);
    state.mem = drift(state.mem, 3 * Math.sqrt(dt), 28, 82);
    state.netSent += (30_000 + Math.random() * 90_000) * dt;
    state.netRecv += (120_000 + Math.random() * 380_000) * dt;
    state.diskRead += (18_000 + Math.random() * 70_000) * dt;
    state.diskWrite += (40_000 + Math.random() * 150_000) * dt;
  }
  setInterval(advance, 1000);

  function human(n) {
    const units = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return n.toFixed(1) + " " + units[i];
  }

  function uptime() {
    const secs = Math.floor((Date.now() - state.boot) / 1000);
    const d = Math.floor(secs / 86400);
    const h = Math.floor((secs % 86400) / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const parts = [];
    if (d) parts.push(d + "d");
    if (h) parts.push(h + "h");
    parts.push(m + "m");
    return {
      string: parts.join(" "),
      boot_time: new Date(state.boot).toISOString().slice(0, 19).replace("T", " "),
      seconds: secs,
    };
  }

  const SERVICES = [
    ["ssh", true], ["cron", true], ["nginx", true], ["docker", true],
    ["systemd-resolved", true], ["ufw", false], ["postgresql", false],
  ];

  const IFACES = [
    { name: "lo", ipv4: "127.0.0.1", is_up: true },
    { name: "eth0", ipv4: "10.0.14.7", is_up: true },
    { name: "wg0", ipv4: "10.66.0.3", is_up: true },
  ];

  const PROC_NAMES = [
    "python3", "node", "nginx", "postgres", "dockerd", "containerd", "sshd",
    "systemd", "chrome", "code", "redis-server", "prometheus", "grafana",
  ];

  function processes() {
    const list = PROC_NAMES.map((name, i) => ({
      pid: 400 + i * 37,
      name,
      cpu_percent: Math.max(0, (Math.random() * (i === 0 ? 40 : 12)) - 1),
      memory_percent: Math.random() * 9,
      status: Math.random() > 0.3 ? "sleeping" : "running",
      username: ["root", "www-data", "postgres", "app"][i % 4],
    }));
    list.sort((a, b) => b.cpu_percent - a.cpu_percent);
    return { processes: list, hidden: false };
  }

  const ROUTES = {
    "/api/config": () => ({
      auth_required: false,
      terminal_enabled: false,
      processes_hidden: false,
      history_points: 60,
      demo: true,
    }),
    "/api/overview": () => ({
      cpu: { percent: state.cpu, cores: CORES, threads: CORES, freq_mhz: Math.round((1400 + Math.random() * 900) * 10) / 10 },
      memory: {
        percent: state.mem,
        used: TOTAL_MEM * state.mem / 100,
        total: TOTAL_MEM,
        used_str: human(TOTAL_MEM * state.mem / 100),
        total_str: human(TOTAL_MEM),
      },
      disk: {
        percent: state.diskPercent,
        used: TOTAL_DISK * state.diskPercent / 100,
        total: TOTAL_DISK,
        used_str: human(TOTAL_DISK * state.diskPercent / 100),
        total_str: human(TOTAL_DISK),
        read_bytes: state.diskRead,
        write_bytes: state.diskWrite,
      },
      network: { bytes_sent: state.netSent, bytes_recv: state.netRecv },
      uptime: uptime(),
      hostname: "demo-node",
      os: "Linux 6.8.0",
    }),
    "/api/metrics": () => ({
      ts: Date.now(),
      cpu: state.cpu,
      mem: state.mem,
      net_sent: state.netSent,
      net_recv: state.netRecv,
      disk_read: state.diskRead,
      disk_write: state.diskWrite,
    }),
    "/api/cpu": () => ({
      overall: state.cpu,
      per_core: Array.from({ length: CORES }, () => drift(state.cpu, 20, 0, 100)),
      cores: CORES,
      threads: CORES,
      freq_current: Math.round((1400 + Math.random() * 900) * 10) / 10,
      freq_max: 2400,
      load_avg: [state.cpu / 100 * CORES, state.cpu / 120 * CORES, state.cpu / 150 * CORES],
    }),
    "/api/memory": () => ({
      ram: {
        total: TOTAL_MEM,
        used: TOTAL_MEM * state.mem / 100,
        free: TOTAL_MEM * (100 - state.mem) / 100,
        percent: state.mem,
        total_str: human(TOTAL_MEM),
        used_str: human(TOTAL_MEM * state.mem / 100),
        free_str: human(TOTAL_MEM * (100 - state.mem) / 100),
      },
      swap: {
        total: TOTAL_SWAP,
        used: TOTAL_SWAP * 0.02,
        percent: 2,
        total_str: human(TOTAL_SWAP),
        used_str: human(TOTAL_SWAP * 0.02),
      },
    }),
    "/api/disk": () => ({
      partitions: [
        { device: "/dev/sda1", mountpoint: "/", fstype: "ext4",
          total_str: human(TOTAL_DISK), used_str: human(TOTAL_DISK * 0.58), free_str: human(TOTAL_DISK * 0.42), percent: 58 },
        { device: "/dev/sda2", mountpoint: "/boot", fstype: "vfat",
          total_str: "512.0 MB", used_str: "94.0 MB", free_str: "418.0 MB", percent: 18 },
        { device: "/dev/sdb1", mountpoint: "/data", fstype: "ext4",
          total_str: "1.8 TB", used_str: "1.3 TB", free_str: "512.0 GB", percent: 72 },
      ],
      io: { read_bytes: state.diskRead, write_bytes: state.diskWrite, read_count: 812344, write_count: 559120 },
    }),
    "/api/network": () => ({
      bytes_sent: state.netSent,
      bytes_recv: state.netRecv,
      packets_sent: 9123044,
      packets_recv: 21882910,
      interfaces: IFACES,
    }),
    "/api/services": () => ({
      services: SERVICES.map(([name, active]) => ({
        name, active, status: active ? "active" : "inactive",
      })),
    }),
    "/api/processes": processes,
  };

  const realFetch = window.fetch ? window.fetch.bind(window) : null;

  window.fetch = function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || "";
    const path = url.replace(/^https?:\/\/[^/]+/, "").split("?")[0];
    const handler = ROUTES[path];
    if (handler) {
      return Promise.resolve(new Response(JSON.stringify(handler()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }));
    }
    if (realFetch) return realFetch(input, init);
    return Promise.reject(new Error("demo: no route for " + path));
  };

  window.addEventListener("load", function () {
    if (typeof window.poll !== "function") return;
    let n = 0;
    const warm = setInterval(function () {
      advance();
      window.poll();
      if (++n >= 45) clearInterval(warm);
    }, 12);
  });

  window.io = function () {
    const listeners = {};
    const socket = {
      on(event, cb) { listeners[event] = cb; return socket; },
      emit() { return socket; },
      disconnect() { return socket; },
    };
    setTimeout(() => {
      if (listeners.connect) listeners.connect();
      if (listeners.terminal_denied) {
        listeners.terminal_denied({ reason: "the interactive shell is disabled in this demo" });
      }
    }, 120);
    return socket;
  };
})();
