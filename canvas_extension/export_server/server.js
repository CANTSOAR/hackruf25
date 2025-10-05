const express = require("express");
const bodyParser = require("body-parser");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 3000;

// Enable CORS for all origins
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.sendStatus(200); // handle preflight
  next();
});

// Folder to store JSON exports
const EXPORT_DIR = path.join(__dirname, "exports");
if (!fs.existsSync(EXPORT_DIR)) fs.mkdirSync(EXPORT_DIR, { recursive: true });

// Parse JSON body
app.use(bodyParser.json({ limit: "50mb" }));

const axios = require("axios");
app.post("/receive_canvas_export", async(req, res) => {
  try {
    const data = req.body;

    if (!data.profile || !data.profile.id) {
      return res.status(400).json({ success: false, error: "Missing profile.uuid in payload" });
    }

    const uuid = data.profile.id;
    const filename = `canvas_export_${uuid}.json`; //this will be how we can get the uuid 
    const filepath = path.join(EXPORT_DIR, filename);

    fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
    console.log(`✅ Saved Canvas export to ${filepath}`);

    await axios.post("http://localhost:5000/api/store_main", {
      profile_id: data.profile.id,
      canvas_json: data
    });

    res.status(200).json({ success: true, file: filename });
  } catch (err) {
    console.error("❌ Failed to save Canvas export:", err);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Canvas export server running at http://localhost:${PORT}`);
});
