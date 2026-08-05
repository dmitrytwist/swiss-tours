import random
import copy
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = "swiss_tournament_secret_key"

tournament = {
    "started": False,
    "max_losses": 3,
    "players": {},         # id: {id, name, wins, losses, eliminated, buchholz, opponents: []}
    "rounds": [],          # История туров: [ {round_num, pairings: [], standings: []} ]
    "current_round": 0
}

def calculate_buchholz_state(players_snapshot):
    """Вычисляет Бухгольц для конкретного снимка игроков на основе их текущих побед."""
    for p_id, p_info in players_snapshot.items():
        opp_ids = p_info["opponents"]
        b_score = sum(players_snapshot[opp]["wins"] for opp in opp_ids if opp in players_snapshot)
        p_info["buchholz"] = b_score

def make_historical_standings():
    """Создает изолированный, отсортированный снимок таблицы строго на текущий момент."""
    players_copy = copy.deepcopy(tournament["players"])
    calculate_buchholz_state(players_copy)
    return sorted(
        players_copy.values(),
        key=lambda x: (not x["eliminated"], x["wins"], x["buchholz"], -x["losses"]),
        reverse=True
    )

def pair_group(players_list):
    """Внутренний хелпер для формирования пар внутри заданной группы игроков."""
    pairings = []
    unpaired = players_list.copy()
    
    while len(unpaired) >= 2:
        p1 = unpaired[0]
        found_partner = False
        
        for i in range(1, len(unpaired)):
            p2 = unpaired[i]
            if p2["id"] not in p1["opponents"]:
                pairings.append({"p1": p1["id"], "p2": p2["id"], "result": None})
                unpaired.remove(p1)
                unpaired.remove(p2)
                found_partner = True
                break
                
        if not found_partner:
            p2 = unpaired[1]
            pairings.append({"p1": p1["id"], "p2": p2["id"], "result": None})
            unpaired.remove(p1)
            unpaired.remove(p2)
            
    return pairings, unpaired

def generate_pairings():
    """Швейцарская жеребьевка с объединением активных и выбывших (без пропусков)."""
    active = [p for p in tournament["players"].values() if not p["eliminated"]]
    eliminated = [p for p in tournament["players"].values() if p["eliminated"]]
    
    calculate_buchholz_state(tournament["players"])
    
    active.sort(key=lambda x: (x["wins"], x["buchholz"]), reverse=True)
    eliminated.sort(key=lambda x: (x["wins"], x["buchholz"]), reverse=True)
    
    final_pairings = []
    active_pairings, active_leftover = pair_group(active)
    final_pairings.extend(active_pairings)
    
    if active_leftover:
        bye_player = active_leftover[0]
        partner_found = False  # Переменная инициализирована корректно
        
        for elim_p in eliminated:
            if elim_p["id"] not in bye_player["opponents"]:
                final_pairings.append({"p1": bye_player["id"], "p2": elim_p["id"], "result": None})
                eliminated.remove(elim_p)
                partner_found = True
                break
                
        # Исправлено имя переменной с found_partner на partner_found
        if not partner_found and eliminated:
            elim_p = eliminated[0]
            final_pairings.append({"p1": bye_player["id"], "p2": elim_p["id"], "result": None})
            eliminated.remove(elim_p)
            
    elim_pairings, elim_leftover = pair_group(eliminated)
    final_pairings.extend(elim_pairings)
    
    if elim_leftover:
        lonely_p = elim_leftover[0]
        all_candidates = sorted(tournament["players"].values(), key=lambda x: (x["eliminated"], x["wins"]), reverse=True)
        for cand in all_candidates:
            if cand["id"] != lonely_p["id"] and cand["id"] not in lonely_p["opponents"]:
                final_pairings.append({"p1": lonely_p["id"], "p2": cand["id"], "result": None})
                break
                
    return final_pairings

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        num_players = int(request.form.get("num_players", 10))
        max_losses = int(request.form.get("max_losses", 3))
        
        tournament.update({
            "started": True, "max_losses": max_losses, "current_round": 1,
            "players": {}, "rounds": []
        })
        
        p_ids = [f"p{i}" for i in range(1, num_players + 1)]
        for i, pid in enumerate(p_ids, 1):
            tournament["players"][pid] = {
                "id": pid, "name": f"Игрок {i}", "wins": 0, "losses": 0,
                "eliminated": False, "buchholz": 0, "opponents": []
            }
            
        random.shuffle(p_ids)
        pairings = []
        unpaired_ids = p_ids.copy()
        
        while len(unpaired_ids) >= 2:
            pairings.append({"p1": unpaired_ids.pop(0), "p2": unpaired_ids.pop(0), "result": None})
            
        if unpaired_ids:
            lonely = unpaired_ids[0]
            partner = random.choice([pid for pid in p_ids if pid != lonely])
            pairings.append({"p1": lonely, "p2": partner, "result": None})

        tournament["rounds"].append({
            "round_num": 1, "pairings": pairings, "standings": make_historical_standings()
        })
        return redirect(url_for("index"))

    return render_template("index.html", tournament=tournament)

@app.route("/generate_results")
def generate_results():
    if not tournament["started"]:
        return redirect(url_for("index"))
        
    curr_round = tournament["rounds"][tournament["current_round"] - 1]
    
    for pair in curr_round["pairings"]:
        if pair["result"]: continue
        
        p1, p2 = pair["p1"], pair["p2"]
        winner, loser = (p1, p2) if random.random() > 0.5 else (p2, p1)
        pair["result"] = {"winner": winner, "loser": loser}
        
        tournament["players"][winner]["wins"] += 1
        tournament["players"][loser]["losses"] += 1
        tournament["players"][winner]["opponents"].append(loser)
        tournament["players"][loser]["opponents"].append(p1 if loser == p2 else p2)

    for pid, pinfo in tournament["players"].items():
        if not pinfo["eliminated"] and pinfo["losses"] >= tournament["max_losses"]:
            pinfo["eliminated"] = True

    curr_round["standings"] = make_historical_standings()
    
    active_players = [p for p in tournament["players"].values() if not p["eliminated"]]
    
    if len(active_players) >= 2:
        tournament["current_round"] += 1
        tournament["rounds"].append({
            "round_num": tournament["current_round"],
            "pairings": generate_pairings(),
            "standings": make_historical_standings()
        })
    else:
        tournament["started"] = False
        
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
