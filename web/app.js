const API = window.ORBITCAST_API || "https://api-13d-8000.sea1.zerops.app";

const stageClass = {
  queued: "border-sky/30 text-ink/55",
  researching: "border-warn text-warn stage-pulse",
  writing: "border-warn text-warn stage-pulse",
  voicing: "border-warn text-warn stage-pulse",
  publishing: "border-warn text-warn stage-pulse",
  published: "border-ok text-ok",
  completed: "border-ok text-ok",
  failed: "border-bad text-bad",
  skipped: "border-ink/20 text-ink/40",
};

const playerEl = () => document.getElementById("player");
const playerBar = () => document.getElementById("player-bar");
let lastListSignature = "";
let currentRemoteUrl = null;

function chip(stage, status) {
  const label = status === "completed" ? "published" : stage || status || "—";
  const cls = stageClass[label] || stageClass[status] || "border-line text-ink/50";
  return `<span class="chip ${cls}">${label}</span>`;
}

function feedUrl(slug) {
  return `${API}/feed/${slug}.xml`;
}

/** Deep links that hand the public RSS URL to installed podcast apps. */
function subscribeApps(rss) {
  const enc = encodeURIComponent(rss);
  const bare = rss.replace(/^https?:\/\//i, "");
  return [
    { name: "Apple Podcasts", href: `podcast://${bare}` },
    { name: "Overcast", href: `overcast://x-callback-url/add?url=${enc}` },
    { name: "Pocket Casts", href: `pktc://subscribe/${enc}` },
    { name: "AntennaPod", href: `pcast://${bare}` },
    { name: "Castro", href: `castro://subscribe/${enc}` },
  ];
}

function subscribeMenu(rss) {
  const apps = subscribeApps(rss)
    .map(
      (a) =>
        `<a href="${a.href}" class="block px-3 py-1.5 text-xs font-mono text-ink/70 hover:bg-ice hover:text-sky">${a.name}</a>`
    )
    .join("");
  return `<details class="relative text-right">
    <summary class="list-none cursor-pointer font-mono text-xs border border-sky text-sky px-2 py-1 rounded-full hover:bg-sky/10 select-none">
      Open in app
    </summary>
    <div class="absolute right-0 mt-1 z-20 min-w-[10.5rem] panel rounded-xl border border-line bg-white shadow-sm overflow-hidden text-left">
      <p class="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wide text-ink/35 font-mono">Subscribe via RSS</p>
      ${apps}
      <button type="button" data-copy="${rss}" class="w-full text-left px-3 py-1.5 text-xs font-mono text-ink/70 hover:bg-ice hover:text-sky border-t border-mist">Copy RSS URL</button>
    </div>
  </details>`;
}

async function copy(text) {
  await navigator.clipboard.writeText(text);
}

function fmtDur(sec) {
  if (!sec && sec !== 0) return "";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

/**
 * Sticky player lives outside the polled feed list so 2s refreshes don't kill playback.
 * Audio is served via API /episodes/{id}/audio (real Range 206 + CORS).
 */
async function playEpisode({ title, remoteUrl, durationSeconds }) {
  const audio = playerEl();
  playerBar().classList.remove("hidden");
  document.getElementById("player-title").textContent = title || "Episode";
  document.getElementById("player-meta").textContent = durationSeconds
    ? `Duration ${fmtDur(durationSeconds)}`
    : "Playing";
  if (currentRemoteUrl !== remoteUrl) {
    currentRemoteUrl = remoteUrl;
    audio.src = remoteUrl;
  }
  try {
    await audio.play();
  } catch (err) {
    console.error(err);
    document.getElementById("player-meta").textContent = `Playback error: ${err.message}`;
  }
}

async function loadMetrics() {
  const m = await fetch(`${API}/metrics`).then((r) => r.json());
  const el = document.getElementById("metrics");
  el.innerHTML = [
    `queue ${m.queue_depth}`,
    `feeds ${m.active_feeds}`,
    `episodes ${m.episodes_completed}/${m.episodes_total}`,
    `failed ${m.episodes_failed}`,
    `skipped ${m.episodes_skipped}`,
    `processing ${m.episodes_processing}`,
  ]
    .map((t) => `<span class="bg-white/80 border border-line rounded-full px-2.5 py-1">${t}</span>`)
    .join("");
}

function signature(feedsPayload) {
  return JSON.stringify(
    feedsPayload.map((f) => ({
      id: f.id,
      latest_status: f.latest_status,
      latest_stage: f.latest_stage,
      latest_episode_id: f.latest_episode_id,
      episode_count: f.episode_count,
      active: f.active,
      error: f.latest_error,
    }))
  );
}

async function loadFeeds({ force = false } = {}) {
  const feeds = await fetch(`${API}/feeds`).then((r) => r.json());
  const sig = signature(feeds);
  if (!force && sig === lastListSignature) return;
  lastListSignature = sig;

  const root = document.getElementById("feeds");
  if (!feeds.length) {
    root.innerHTML = `<p class="text-ink/45 font-mono text-sm">No feeds yet — create one above.</p>`;
    return;
  }

  const cards = await Promise.all(
    feeds.map(async (f) => {
      const detail = await fetch(`${API}/feeds/${f.id}`).then((r) => r.json());
      const episodes = detail.episodes || [];
      const rss = feedUrl(f.slug);
      const epRows = episodes
        .slice(0, 8)
        .map((e) => {
          const retry =
            e.status === "failed" || e.status === "skipped"
              ? `<button data-retry="${e.id}" class="underline text-bad text-xs">retry</button>`
              : "";
          const play =
            e.status === "completed" && e.audio_url
              ? `<button
                  data-play-url="${API}/episodes/${e.id}/audio"
                  data-play-title="${(e.title || "Episode").replaceAll('"', "&quot;")}"
                  data-play-dur="${e.duration_seconds || ""}"
                  class="font-mono text-xs border border-sky text-sky px-2 py-0.5 rounded-full hover:bg-sky/10"
                >Play</button>`
              : "";
          const dur = e.duration_seconds
            ? `<span class="text-xs font-mono text-ink/35">${fmtDur(e.duration_seconds)}</span>`
            : "";
          return `<li class="flex flex-wrap items-center gap-2 py-2 border-b border-mist last:border-0">
            ${chip(e.stage, e.status)}
            <span class="text-sm flex-1 min-w-[10rem]">${e.title || "Untitled"}</span>
            ${dur}
            ${play}
            ${retry}
            ${e.error ? `<span class="text-xs text-bad font-mono w-full">${e.error}</span>` : ""}
          </li>`;
        })
        .join("");

      const paused =
        f.active === false
          ? `<span class="chip border-ink/20 text-ink/40">paused</span>`
          : "";

      return `<article class="panel rounded-2xl p-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 class="text-xl font-semibold">${f.title}</h3>
            <p class="text-sm text-ink/55 mt-1 max-w-xl">${f.topic_prompt}</p>
            <p class="font-mono text-xs text-ink/35 mt-2">slug ${f.slug} · every ${f.schedule_minutes}m · ${f.episode_count} episodes · recap ${f.recap_previous === false ? "off" : "on"} ${paused}</p>
          </div>
          <div class="flex flex-col items-end gap-2">
            ${chip(f.latest_stage, f.latest_status)}
            ${subscribeMenu(rss)}
            <button data-refresh="${f.id}" class="font-mono text-xs border border-line text-ink/70 px-2 py-1 rounded-full hover:border-sky/50">Refresh (force ep)</button>
          </div>
        </div>
        <ul class="mt-4">${epRows || '<li class="text-ink/40 text-sm">No episodes yet</li>'}</ul>
      </article>`;
    })
  );

  root.innerHTML = cards.join("");

  root.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await copy(btn.dataset.copy);
      const prev = btn.textContent;
      btn.textContent = "Copied";
      setTimeout(() => (btn.textContent = prev), 1200);
    });
  });
  root.querySelectorAll("details").forEach((d) => {
    d.addEventListener("toggle", () => {
      if (!d.open) return;
      root.querySelectorAll("details").forEach((other) => {
        if (other !== d) other.open = false;
      });
    });
  });
  root.querySelectorAll("[data-refresh]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      await fetch(`${API}/feeds/${btn.dataset.refresh}/refresh`, { method: "POST" });
      btn.disabled = false;
      lastListSignature = "";
      await refresh({ force: true });
    });
  });
  root.querySelectorAll("[data-retry]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch(`${API}/episodes/${btn.dataset.retry}/retry`, { method: "POST" });
      lastListSignature = "";
      await refresh({ force: true });
    });
  });
  root.querySelectorAll("[data-play-url]").forEach((btn) => {
    btn.addEventListener("click", () => {
      playEpisode({
        title: btn.dataset.playTitle,
        remoteUrl: btn.dataset.playUrl,
        durationSeconds: Number(btn.dataset.playDur) || null,
      });
    });
  });
}

async function refresh({ force = false } = {}) {
  try {
    await Promise.all([loadMetrics(), loadFeeds({ force })]);
  } catch (err) {
    console.error(err);
    document.getElementById("form-status").textContent = `API error: ${err.message}`;
  }
}

document.getElementById("create-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    title: fd.get("title"),
    topic_prompt: fd.get("topic_prompt"),
    schedule_minutes: Number(fd.get("schedule_minutes") || 60),
    recap_previous: fd.get("recap_previous") === "on",
  };
  const status = document.getElementById("form-status");
  status.textContent = "Creating…";
  const res = await fetch(`${API}/feeds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    status.textContent = `Failed: ${await res.text()}`;
    return;
  }
  const feed = await res.json();
  status.textContent = `Created ${feed.slug} — episode queued`;
  e.target.reset();
  lastListSignature = "";
  await refresh({ force: true });
});

refresh({ force: true });
setInterval(() => refresh({ force: false }), 2000);
