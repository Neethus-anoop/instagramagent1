export default function handler(req, res) {
  const VERIFY_TOKEN = "mytoken123";

  // Verification
  if (req.method === "GET") {
    const mode = req.query["hub.mode"];
    const token = req.query["hub.verify_token"];
    const challenge = req.query["hub.challenge"];

    if (mode && token === VERIFY_TOKEN) {
      return res.status(200).send(challenge);
    } else {
      return res.status(403).send("Verification failed");
    }
  }

  // Receive messages
  if (req.method === "POST") {
    console.log("Webhook Event:", req.body);
    return res.status(200).send("EVENT_RECEIVED");
  }

  res.status(405).end();
}
