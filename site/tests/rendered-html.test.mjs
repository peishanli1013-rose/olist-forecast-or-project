import assert from "node:assert/strict";
import test from "node:test";

async function render(pathname = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${pathname}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`https://olist-or.example${pathname}`, {
      headers: {
        accept: "text/html",
        host: "olist-or.example",
        "x-forwarded-host": "olist-or.example",
        "x-forwarded-proto": "https",
      },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the Olist OR dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Olist OR Lab<\/title>/i);
  assert.match(html, /From marketplace signals to inventory decisions\./);
  assert.match(html, /13-week rolling backtest/);
  assert.match(html, /Open sensitivity lab/);
  assert.match(html, /27 checks passed/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Starter Project/i);
});

test("emits complete absolute social metadata", async () => {
  const response = await render();
  const html = await response.text();

  assert.match(html, /property="og:title" content="Olist OR Lab"/);
  assert.match(html, /property="og:image" content="https:\/\/olist-or\.example\/og\.png"/);
  assert.match(html, /name="twitter:card" content="summary_large_image"/);
  assert.match(html, /name="twitter:image" content="https:\/\/olist-or\.example\/og\.png"/);
});
