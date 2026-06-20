import https from "node:https";

function fail(message) {
  process.stderr.write(String(message));
  process.exit(1);
}

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  raw += chunk;
});
process.stdin.on("end", () => {
  let payload;
  try {
    payload = JSON.parse(raw || "{}");
  } catch (error) {
    fail(`Invalid helper input JSON: ${error instanceof Error ? error.message : String(error)}`);
    return;
  }

  const url = typeof payload.url === "string" ? payload.url : "";
  const apiKey = typeof payload.api_key === "string" ? payload.api_key : "";
  const timeoutSeconds =
    typeof payload.timeout_seconds === "number" && Number.isFinite(payload.timeout_seconds)
      ? payload.timeout_seconds
      : 120;
  const body = JSON.stringify(payload.body ?? {});

  if (!url || !apiKey) {
    fail("Node transport requires both url and api_key.");
    return;
  }

  const req = https.request(
    url,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
      timeout: timeoutSeconds * 1000,
    },
    (res) => {
      let responseText = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => {
        responseText += chunk;
      });
      res.on("end", () => {
        let parsedBody;
        try {
          parsedBody = JSON.parse(responseText);
        } catch {
          parsedBody = responseText;
        }
        const result = {
          ok: (res.statusCode ?? 500) >= 200 && (res.statusCode ?? 500) < 300,
          status: res.statusCode ?? 500,
          response: typeof parsedBody === "object" && parsedBody !== null ? parsedBody : null,
          body: typeof parsedBody === "string" ? parsedBody : JSON.stringify(parsedBody),
        };
        process.stdout.write(JSON.stringify(result));
      });
    },
  );

  req.on("timeout", () => {
    req.destroy(new Error("Request timed out."));
  });
  req.on("error", (error) => {
    fail(error instanceof Error ? error.message : String(error));
  });
  req.write(body);
  req.end();
});
