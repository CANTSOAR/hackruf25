const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");

const app = express();
const PORT = 3000;

// Enable CORS
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.sendStatus(200);
  next();
});

// Parse JSON body
app.use(bodyParser.json({ limit: "50mb" }));

app.post("/receive_canvas_export", async (req, res) => {
  try {
    const data = req.body;

    if (!data.profile || !data.profile.id) {
      return res.status(400).json({ success: false, error: "Missing profile.id in payload" });
    }

    // Forward to Flask
    const flaskResp = await axios.post("http://scarletagent.tech/api/integrations/canvas/save", data, {
      headers: { "Content-Type": "application/json" },
    });

    res.status(flaskResp.status).json({
      success: true,
      flask_response: flaskResp.data
    });
  } catch (err) {
    console.error("❌ Failed to forward Canvas export:", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Canvas export server running at http://localhost:${PORT}`);
});
