# Trivia Answer Reveal — Browser Version

A small browser-based version of the Tkinter trivia answer game. One host creates a room; players join from phones or computers using a five-character room code.

## Features

- Real-time answer submissions and submission status
- Answers stay hidden until the host reveals them
- Host-only controls for revealing/hiding answers, resetting answers for the current question, and moving to the next question
- Reset confirmation
- Mobile-friendly layout

## Run locally

Requires Python 3.10 or newer.

1. Unzip the project and open a terminal in the `trivia_browser_game` directory.
2. Create and activate a virtual environment (recommended).
3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the server:

   ```bash
   python app.py
   ```

5. Open `http://127.0.0.1:5000` in your browser.
6. Click **Create host room**. Share the room code with players.

### Let people on the same Wi-Fi join

Find the host computer's local IP address and have players open `http://YOUR-LOCAL-IP:5000`. The host computer and players need to be on the same network, and the computer firewall must allow inbound connections on port 5000.

### Host it publicly

Deploy the app to a Python web host that supports Flask-SocketIO/WebSockets. Set the service's start command to `python app.py` and use the host-provided HTTPS URL. Do not expose the app to the public internet without adding stronger host authentication and persistent storage appropriate to your use case.

## Important starter-version notes

- Active rooms are held in memory and are cleared if the server restarts.
- A room is intended for a single trivia session.
- The host token is kept in the host browser page; host actions are validated on the server. Do not share the host browser session or host token.
- This starter version does not have durable player identities or a database. A disconnected player is removed from the live roster.
- The Socket.IO client is loaded from a CDN, so the browser needs internet access to load that script.
