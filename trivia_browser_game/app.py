import secrets
import string
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins=[])

# Active rooms live in memory. For a small trivia night this is simple and fast;
# active games are cleared if the server restarts.
rooms = {}
sid_membership = {}


def room_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(5))
        if code not in rooms:
            return code


def public_state(code):
    room = rooms[code]
    answers = room["answers"]
    revealed = room["revealed"]
    return {
        "code": code,
        "question_number": room["question_number"],
        "question": room["question"],
        "locked": room["locked"],
        "revealed": revealed,
        "players": [
            {
                "name": player["name"],
                "submitted": player["sid"] in answers,
                "answer": answers.get(player["sid"]) if revealed else None,
            }
            for player in room["players"].values()
        ],
        "answer_count": len(answers),
        "player_count": len(room["players"]),
    }


def broadcast_state(code):
    if code in rooms:
        emit("state", public_state(code), to=code)


def error(message):
    emit("notice", {"message": message})


def current_room():
    membership = sid_membership.get(request.sid)
    if not membership:
        return None, None
    code, role, player_id = membership
    if code not in rooms:
        return None, None
    return rooms[code], (code, role, player_id)


def is_host(room, membership):
    if not membership:
        return False
    code, role, token = membership
    return role == "host" and secrets.compare_digest(token, room["host_token"])


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("create_room")
def create_room(data):
    name = (data.get("name") or "Host").strip()[:30] or "Host"
    code = room_code()
    token = secrets.token_urlsafe(32)
    rooms[code] = {
        "host_token": token,
        "host_sid": request.sid,
        "host_name": name,
        "question_number": 1,
        "question": "Enter your first trivia question in the host panel.",
        "locked": False,
        "revealed": False,
        "players": {},
        "answers": {},
    }
    sid_membership[request.sid] = (code, "host", token)
    join_room(code)
    emit("room_created", {"code": code, "host_token": token, "name": name})
    broadcast_state(code)


@socketio.on("join_room")
def handle_join(data):
    code = (data.get("code") or "").strip().upper()
    name = (data.get("name") or "").strip()[:30]
    if not name:
        return error("Please enter your name.")
    room = rooms.get(code)
    if not room:
        return error("That room code wasn't found. Check the code and try again.")
    if request.sid in sid_membership:
        old_code, _, _ = sid_membership[request.sid]
        if old_code in rooms:
            rooms[old_code]["players"].pop(request.sid, None)
            rooms[old_code]["answers"].pop(request.sid, None)
            socketio.emit("state", public_state(old_code), to=old_code)
        sid_membership.pop(request.sid, None)

    room["players"][request.sid] = {"name": name, "sid": request.sid}
    sid_membership[request.sid] = (code, "player", request.sid)
    join_room(code)
    emit("joined_room", {"code": code, "name": name})
    broadcast_state(code)


@socketio.on("submit_answer")
def submit_answer(data):
    room, membership = current_room()
    if not room or not membership or membership[1] != "player":
        return error("Join a game as a player before submitting.")
    code, _, player_id = membership
    answer = (data.get("answer") or "").strip()[:500]
    if not answer:
        return error("Enter an answer before submitting.")
    if room["locked"]:
        return error("Submissions are locked for this question.")
    if room["revealed"]:
        return error("Answers have already been revealed. Wait for the next question.")
    room["answers"][player_id] = answer
    emit("submission_saved", {"message": "Answer submitted!"})
    broadcast_state(code)


@socketio.on("host_action")
def host_action(data):
    room, membership = current_room()
    if not room or not is_host(room, membership):
        return error("Only the host can do that.")
    code = membership[0]
    action = data.get("action")

    if action == "set_question":
        question = (data.get("question") or "").strip()[:500]
        if not question:
            return error("Please enter a question.")
        room["question"] = question
        room["answers"].clear()
        room["locked"] = False
        room["revealed"] = False
    elif action == "lock":
        room["locked"] = True
    elif action == "unlock":
        if room["revealed"]:
            return error("Start a new question before unlocking submissions.")
        room["locked"] = False
    elif action == "reveal":
        room["locked"] = True
        room["revealed"] = True
    elif action == "hide":
        room["revealed"] = False
        # Keep locked state unchanged; host can choose whether submissions remain locked.
    elif action == "reset":
        room["answers"].clear()
        room["revealed"] = False
        room["locked"] = False
    elif action == "next_question":
        room["question_number"] += 1
        room["question"] = (data.get("question") or "").strip()[:500] or "Enter the next question in the host panel."
        room["answers"].clear()
        room["revealed"] = False
        room["locked"] = False
    else:
        return error("Unknown host action.")

    broadcast_state(code)


@socketio.on("disconnect")
def disconnect():
    membership = sid_membership.pop(request.sid, None)
    if not membership:
        return
    code, role, _ = membership
    room = rooms.get(code)
    if not room:
        return
    if role == "player":
        room["players"].pop(request.sid, None)
        room["answers"].pop(request.sid, None)
        broadcast_state(code)
    # Keep the room available if the host disconnects; the host can reconnect
    # by refreshing only if they still have the host token in the same page.
    # For this starter version, host controls require the original socket session.


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
