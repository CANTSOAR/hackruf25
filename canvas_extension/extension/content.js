(async () => {
  try {
    async function pagedFetch(url) {
      const results = [];
      let nextUrl = url;
      while (nextUrl) {
        const r = await fetch(nextUrl, { credentials: "include" });
        if (!r.ok) throw new Error("HTTP " + r.status);
        const data = await r.json();
        results.push(...(Array.isArray(data) ? data : [data]));
        const link = r.headers.get("link");
        if (!link) break;
        const next = link.split(",").find(p => p.includes('rel="next"'));
        nextUrl = next ? next.slice(next.indexOf("<") + 1, next.indexOf(">")) : null;
      }
      return results;
    }

    console.log("Canvas Auto Exporter: collecting data…");
    const base = location.origin;

    const profileResp = await fetch(`${base}/api/v1/users/self/profile`, { credentials: "include" });
    if (!profileResp.ok) throw new Error("Profile fetch failed: " + profileResp.status);
    const profile = await profileResp.json();

    const uid = {{CANVAS_USER_ID}};
    profile.id = uid;
    const courses = await pagedFetch(`${base}/api/v1/users/${uid}/courses?per_page=100&include[]=term`);

    for (const c of courses) {
      try { c.assignments = await pagedFetch(`${base}/api/v1/courses/${c.id}/assignments?per_page=100`); } catch { c.assignments = []; }
      try { c.files = await pagedFetch(`${base}/api/v1/courses/${c.id}/files?per_page=100`); } catch { c.files = []; }
      try { c.announcements = await pagedFetch(`${base}/api/v1/courses/${c.id}/discussion_topics?only_announcements=true&per_page=100`); } catch { c.announcements = []; }
    }

    const payload = { profile, courses, collected_at: new Date().toISOString() };

    const serverUrl = "https://scarletagent.tech/api/receive_canvas_export";
    await fetch(serverUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    console.log("Canvas Auto Exporter: upload complete.");
  } catch (err) {
    console.error("Canvas Auto Exporter failed:", err);
  }
})();