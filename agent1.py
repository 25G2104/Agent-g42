import random
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from IPython import display

# ==========================================
# 条件設定
# ==========================================

# モバイルオーダー
MOBILE_ORDER_ENABLED = True # モバイルオーダーのオン・オフ
MOBILE_ORDER_RATIO = 0.5    # モバイルオーダーを利用する割合(0.0〜1.0)

#　席の時間制限
SEAT_RESTRICT = 'SHORT' # SHORTは10～20、NORMALは15～25、LONGは20～30をeating_durationに指定する。

#　受け取り口増やす　
EXPAND_PICKUP_COUNTER = False

# メニュー
MENU_CURRY = 0
MENU_SETMEAL = 1
MENU_NOODLE = 2

# 各メニューのカウンターレーン（x座標）
# EXPAND_PICKUP_COUNTER=True で全メニュー2レーンずつに増設
if EXPAND_PICKUP_COUNTER:
    MENU_LANES = {MENU_CURRY: [12, 16], MENU_SETMEAL: [22, 26], MENU_NOODLE: [32, 36]}
else:
    MENU_LANES = {MENU_CURRY: [14], MENU_SETMEAL: [24], MENU_NOODLE: [34]}
ALL_LANES = [lane for lanes in MENU_LANES.values() for lane in lanes]

# モバイル受け取り枠の上限（同時に取りに行ける人数）＝レーン数×3
MOBILE_PICKUP_CAPACITY = len(ALL_LANES) * 3

#　不満度の設定
WAIT_TOLERANCE = 40 # この待ちステップ数までは不満度0（許容範囲）
DISSAT_PER_STEP = 0.4 # 許容を超えた1ステップあたりの不満度

# ロール比率
ROLE_WEIGHTS = {'WAITING': 70, 'DIRECT': 20, 'STAYER': 10}

# ==========================================
# 1. レイアウト
# ==========================================
WIDTH = 45
HEIGHT = 30
BASE_MAP = [["." for _ in range(WIDTH)] for _ in range(HEIGHT)]

# 外壁
for x in range(WIDTH):
    BASE_MAP[0][x] = "W"
    BASE_MAP[HEIGHT-1][x] = "W"
for y in range(HEIGHT):
    BASE_MAP[y][0] = "W"
    BASE_MAP[y][WIDTH-1] = "W"

# キッチンエリア（y=1〜4）
for y in range(1, 5):
    for x in range(1, WIDTH-1): 
        BASE_MAP[y][x] = "K"

# カウンター提供口（y=5）
for lane in ALL_LANES:
    BASE_MAP[5][lane] = "C"

# 返却口（右上奥 y=5〜7）
for y in range(5, 8):
    for x in range(38, 42): 
        BASE_MAP[y][x] = "H"

# 出入り口（1つだけ）
BASE_MAP[HEIGHT-1][2] = "D"  # 入口のみ

# 券売機（3台）
BASE_MAP[12][2] = "R"
BASE_MAP[16][2] = "R"
BASE_MAP[20][2] = "R"

# 席と券売機の境界だけ中央に壁を置く
for y in range(10, 21):
    BASE_MAP[y][9] = "W"

# 並び列スペース（水色）
for y in range(6, 26):
    for x in range(1, 4):  # 券売機前
        BASE_MAP[y][x] = "Q"
    for x in range(5, 9):  # 出口ルート
        BASE_MAP[y][x] = "Q"

# カウンター列
for y in range(6, 13):
    for lane in ALL_LANES:
        BASE_MAP[y][lane] = "Q"

# 座席（T）の配置 ＆ 座標リストの自動回収
SEATS = []
for y in range(16, 28, 3):
    for x in range(11, 42, 3):
        for dy in range(2):
            for dx in range(2):
                if BASE_MAP[y+dy][x+dx] == ".": 
                    BASE_MAP[y+dy][x+dx] = "T"
                    SEATS.append((x+dx, y+dy)) # 空いている座席座標を記録

# 色変換用
SYMBOL_TO_INT = {".": 0, "W": 1, "D": 2, "R": 3, "Q": 4, "C": 5, "K": 6, "T": 7, "H": 8}
COLOR_LIST = ["white", "black", "limegreen", "royalblue", "skyblue", "orange", "darkgray", "peru", "mediumpurple"]
numeric_map = [[SYMBOL_TO_INT[cell] for cell in row] for row in BASE_MAP]

# 固定座標の定義
ENTRANCE = (2, HEIGHT-2) 
TICKET_MACHINES = [(2, 12), (2, 16), (2, 20)]

# メニュー→受け取り口座標（MENU_LANESから生成）
COUNTERS = {menu: [(lane, 5) for lane in lanes] for menu, lanes in MENU_LANES.items()}


# 壁を迂回するための「安全な通路（チェックポイント）」
CORRIDOR_X = 6      # 券売機と席の間にある縦の通路(Q)のX座標
WAITING_PASS_Y = 5  # カウンター前のY座標
DIRECT_PASS_Y = 24   # 壁(y=10〜20)の下をくぐる安全なY座標

# ==========================================
# 列のデータ構造
# ==========================================
QUEUE_TICKET = [(2, y) for y in range(6, 26)]
ticket_queue = []  

QUEUE_COUNTER = {lane: [(lane, y) for y in range(6, 13)] for lane in ALL_LANES}

counter_queues = {lane: [] for lane in ALL_LANES}

ticket_busy = [False, False, False]
counter_busy = {lane: False for lane in ALL_LANES}

#モバイルオーダー
mobile_ready = [] # 受け取り待ちのモバイル客
mobile_picking = [0] # 受け取りに向かっている客

satisfaction_log = []   # (role, dissatisfaction) を食事開始時に記録
def compute_dissatisfaction(wait):
    # 許容を超えた待ち時間に比例、0〜100でクリップ
    return min(100, max(0, (wait - WAIT_TOLERANCE) * DISSAT_PER_STEP))

# ==========================================
# 2. エージェントとグループのロジック
# ==========================================
class Group:
    def __init__(self, group_id, size, base_duration):
        self.group_id = group_id
        self.total_count = size
        self.seated_count = 0
        self.eating_duration = random.randint(6, 20)
        self.timer_started = False
        self.is_stayer_group = random.random() < 0.5 
        self.assigned_seats = []
        self.leader_seated = False


    def leader_member_seated(self):
        """赤（リーダー）が座ったらタイマー開始"""
        self.leader_seated = True
        self.timer_started = True
        if self.is_stayer_group:
            # SEAT_RESTRICTで5分刻みで、どれくらい長く滞在させるか３段階の変更ができる
            if SEAT_RESTRICT == 'NORMAL':
                self.eating_duration = random.randint(15, 25) 
            elif SEAT_RESTRICT == 'SHORT':
                self.eating_duration = random.randint(10, 20)
            elif SEAT_RESTRICT == 'LONG':
                self.eating_duration = random.randint(20, 30)
        print(f"  [Group {self.group_id}] リーダーが座りました！タイマー開始。")
    
    def member_seated(self):
        self.seated_count += 1
        if self.seated_count == self.total_count:
            self.timer_started = True
            if self.is_stayer_group:
                if SEAT_RESTRICT == 'NORMAL':
                    self.eating_duration = random.randint(15, 25)
                elif SEAT_RESTRICT == 'SHORT':
                    self.eating_duration = random.randint(10, 20)
                elif SEAT_RESTRICT == 'LONG':
                    self.eating_duration = random.randint(20, 30)
            print(f"  [Group {self.group_id}] 全員揃いました！タイマー開始。")

class Agent:
    def __init__(self, agent_id, role, group):
        self.agent_id = agent_id
        self.role = role 
        self.group = group
        self.x, self.y = ENTRANCE
        self.seat_xy = None
        self.path = [] 
        self.state = 'INITIAL'
        self.queue_index = None      
        self.counter_lane = None
        self.notify_timer = None
        self.serve_timer = None # 受け取り口での受け取りにかかる残りステップ
        self.wait_time = 0 # 食べ始めるまでの待ちステップ数
        self.dissatisfaction = None # 食事開始時に確定
        self.menu = random.choices(
            [MENU_CURRY, MENU_SETMEAL, MENU_NOODLE],
            weights=[15, 40, 45],
            k=1
        )[0]     
        self.generate_initial_path()

    def move_toward(self, tx, ty):
        nx, ny = self.x, self.y

        # x方向
        if self.x < tx:
            if BASE_MAP[self.y][self.x + 1] != "W":
                nx = self.x + 1
        elif self.x > tx:
            if BASE_MAP[self.y][self.x - 1] != "W":
                nx = self.x - 1

        # y方向
        if self.y < ty:
            if BASE_MAP[self.y + 1][self.x] != "W":
                ny = self.y + 1
        elif self.y > ty:
            if BASE_MAP[self.y - 1][self.x] != "W":
                ny = self.y - 1

        self.x, self.y = nx, ny

    def generate_initial_path(self):
        """初期の経路生成（移動中の上書きを防ぐため、状態遷移ごとにpathを設定する方針に変更）"""
        if self.role != 'WAITING':
             # DIRECT / STAYER は、中央の壁を避けて下側を迂回して席の近くまで進む
            self.path.append((CORRIDOR_X, ENTRANCE[1]))    
            self.path.append((CORRIDOR_X, DIRECT_PASS_Y))  
            self.state = 'PROCESS'

    def update(self):
        # 食べ始める前・在店中だけ待ち時間を数える
        if self.dissatisfaction is None and (self.x, self.y) != (-1, -1):
            self.wait_time += 1
        # 1. 券売機列に並んでいる状態
        if self.role == 'WAITING' and self.state == 'INITIAL':
            if self.queue_index < len(QUEUE_TICKET):
                tx, ty = QUEUE_TICKET[self.queue_index]
            else:
                tx, ty = QUEUE_TICKET[-1] # あふれた場合は最後尾

            # 前の人が進んだら詰める
            if self.queue_index > 0:
                front = ticket_queue[self.queue_index - 1]
                if front.y < self.y -1:
                    self.y -= 1
                    return

            if (self.x, self.y) != (tx, ty):
                if self.x < tx: self.x += 1
                elif self.x > tx: self.x -= 1
                if self.y < ty: self.y += 1
                elif self.y > ty: self.y -= 1
                return

            if self.queue_index == 0:
                self.state = "BUY_TICKET"
                return

        # 2. 券売機を物色・購入へ向かう
        if self.state == "BUY_TICKET":
            for i, (tx, ty) in enumerate(TICKET_MACHINES):
                if not ticket_busy[i]:
                    ticket_busy[i] = True
                    self.path = [(tx, ty)]
                    self.state = "TO_TICKET_MACHINE"
                    
                    # 列から抜けて後続を詰める
                    if ticket_queue and ticket_queue[0] == self:
                        ticket_queue.pop(0)
                        for j, ag in enumerate(ticket_queue):
                            ag.queue_index = j
                    return
            return # 空きが出るまで待機

        # 3. 券売機の目の前まで移動
        if self.state == "TO_TICKET_MACHINE":
            if self.path:
                tx, ty = self.path[0]
                # if self.x < tx: self.x += 1
                # elif self.x > tx: self.x -= 1
                # if self.y < ty: self.y += 1
                # elif self.y > ty: self.y -= 1
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                # 券売機での購入完了（簡易的に即完了）
                # 使用状態を解放
                for i, (tx, ty) in enumerate(TICKET_MACHINES):
                    if (self.x, self.y) == (tx, ty):
                        ticket_busy[i] = False
                
                # メニューに対応する候補レーンから、一番空いている列を選ぶ
                candidates = MENU_LANES[self.menu]
                lane = min(
                    candidates,
                    key=lambda x: len(counter_queues[x])
                )
                self.counter_lane = lane
                self.queue_index = len(counter_queues[lane])
                counter_queues[lane].append(self)
                self.state = "QUEUE_COUNTER"
                return

        # 4. カウンター列の動き（インデント修正）
        if self.state == "QUEUE_COUNTER":
            lane = self.counter_lane
            queue = counter_queues[lane]
            path = QUEUE_COUNTER[lane]

            if self.queue_index < len(path):
                tx, ty = path[self.queue_index]
            else:
                tx, ty = path[-1]

            if (self.x, self.y) != (tx, ty):
                # if self.x < tx: self.x += 1
                # elif self.x > tx: self.x -= 1
                # if self.y < ty: self.y += 1
                # elif self.y > ty: self.y -= 1
                self.move_toward(tx, ty)
                return

            if self.queue_index == 0:
                self.state = "AT_COUNTER"
                return

        # 5. カウンターでの受け取り要求
        if self.state == "AT_COUNTER":
            lane = self.counter_lane
            queue = counter_queues[lane]
            if not counter_busy[lane]:
                counter_busy[lane] = True
                cx, cy = lane, 5
                self.path = [(cx, cy)]
                self.state = "TO_COUNTER_SPOT"
                
                # カウンター列から抜ける
                if queue and queue[0] == self:
                    counter_queues[lane].pop(0)
                    for j, ag in enumerate(counter_queues[lane]):
                        ag.queue_index = j
                return
            return

        # 6. カウンターの目の前へ移動して受け取り
        if self.state == "TO_COUNTER_SPOT":
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)

                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                # 受け取りにかかる時間（この間 counter_busy は True のまま＝次の人は待つ）
                if self.serve_timer is None:
                    self.serve_timer = random.randint(1, 5)
                if self.serve_timer > 0:
                    self.serve_timer -= 1
                    return
                # 受け取り完了 → カウンター解放
                counter_busy[self.counter_lane] = False
                self.serve_timer = None
                if self.role == 'MOBILE':
                    self.path = [(self.seat_xy[0], WAITING_PASS_Y), self.seat_xy]
                    self.state = 'RETURN_TO_SEAT'
                else:
                    # 席へ移動する状態へ遷移
                    self.state = "PROCESS"
                return

        if self.state == 'RETURN_TO_SEAT':
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                self.state = 'SEATED_WAITING'
                self.group.member_seated()
                return

        # 7. 席の割り当てと移動
        if self.state == 'PROCESS':
            if self.seat_xy is None:
                if self.group.assigned_seats:
                    seat = self.group.assigned_seats.pop(0)

                    if seat == "WAIT":
                        if SEATS:
                            self.seat_xy = SEATS.pop(0)
                        else:
                            self.state = 'LEAVE'
                            self.path = [ENTRANCE]
                            return
                    
                    self.seat_xy = seat
                    
                    # 経由地を含めた最終的な席へのルートを作成
                    if self.role == 'WAITING':
                        self.path = [(CORRIDOR_X, ENTRANCE[1]), (CORRIDOR_X, WAITING_PASS_Y), 
                                    (self.seat_xy[0], WAITING_PASS_Y), self.seat_xy]
                    else:
                        self.path =[(CORRIDOR_X, ENTRANCE[1]), (CORRIDOR_X, DIRECT_PASS_Y), 
                                    (self.seat_xy[0], DIRECT_PASS_Y), self.seat_xy]
                    return
                else:

                    # self.state = 'MOVING_TO_SEAT'
                    return
                
            if self.path:
                tx,ty = self.path[0]
                self.move_toward(tx,ty)
                # if self.x < tx: self.x += 1
                # elif self.x > tx: self.x -= 1
                # if self.y < ty: self.y += 1
                # elif self.y > ty: self.y -= 1
                if (self.x , self.y) == (tx,ty):
                    self.path.pop(0)
                
            else: #席に到達済み
                if self.role == 'MOBILE':
                    self.state = 'MOBILE_WAITING'
                    self.notify_timer = random.randint(1, 5)  #注文から調理完了
                else:
                    self.state = 'SEATED_WAITING'
                    self.group.member_seated()
                return

        # MOBILE： 席で待ち、カウンター列へ合流
        if self.state == 'MOBILE_WAITING':
            if self.notify_timer is not None:
                self.notify_timer -= 1
                if self.notify_timer <= 0:
                    self.notify_timer = None
                    mobile_ready.append(self)
            # 受け取り中の客が上限未満 かつ 自分が待ちの先頭なら取りに行く
            if (mobile_ready and mobile_ready[0] is self and mobile_picking[0] < MOBILE_PICKUP_CAPACITY):
                mobile_ready.pop(0)
                mobile_picking[0] += 1
                lane = min(counter_queues.keys(), key=lambda k: abs(k - self.seat_xy[0]))
                self.counter_lane = lane
                self.path = [(lane, WAITING_PASS_Y)]  # 受け取り口(カウンターに重ねて表示)
                self.state = 'MOBILE_PICKUP'
            return

        # MOBILE：受け取り口へ移動→受け取ったら席へ戻る
        if self.state == 'MOBILE_PICKUP':
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                mobile_picking[0] -= 1   # 受け取り完了、枠を1つ空ける
                self.path = [(self.seat_xy[0], WAITING_PASS_Y), self.seat_xy]
                self.state = 'RETURN_TO_SEAT'
            return

        # グループが全員揃ってタイマーが動いていたら食事状態に遷移させる
        if self.state == 'SEATED_WAITING':
            if self.group.seated_count >= 1:
                self.state = 'EATING'
                self.dissatisfaction = compute_dissatisfaction(self.wait_time)
                satisfaction_log.append((self.role, self.dissatisfaction))

        # 8. 食事中（タイマー終了を監視）
        if self.state == 'EATING':
            if self.group.eating_duration <= 0:
                if self.role == 'WAITING':
                    self.path = [(40, 6)]   # 返却口
                    self.state = 'TO_RETURN'
                else:
                    self.path = [ENTRANCE]  # 直接出口へ
                    self.state = 'LEAVE'
                
                # 立ち上がったので座席を返却
                if self.state == 'LEAVE'and not self.path:
                    #完全退店
                    if self.seat_xy:
                        SEATS.append(self.seat_xy)
                        self.seat_xy = None
                    self.x, self.y = -1,-1
                    return

        # 9. 返却口へ向かう
        if self.state == 'TO_RETURN':
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                # if self.x < tx: self.x += 1
                # elif self.x > tx: self.x -= 1
                # if self.y < ty: self.y += 1
                # elif self.y > ty: self.y -= 1
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                self.path = [ENTRANCE]
                self.state = 'LEAVE'
                return

        # 10. 退店（出口へ向かう）
        if self.state == 'LEAVE':
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                # if self.x < tx: self.x += 1
                # elif self.x > tx: self.x -= 1
                # if self.y < ty: self.y += 1
                # elif self.y > ty: self.y -= 1
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                # 完全退店
                if self.seat_xy:
                    SEATS.append(self.seat_xy)
                    self.seat_xy = None
                self.x, self.y = -1, -1

# ==========================================
# 3. 実行とアニメーション描画
# ==========================================
all_agents = []
all_groups = []
x_history = []
y_history = []
d_history = []          # 不満度（累積平均）の履歴
agent_id_counter = 1
group_id_counter = 101

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))
ax2b = ax2.twinx()      # 不満度用の右側の軸


# シミュレーション
for step in range(1, 1201):
    ax1.clear()
    
    # 1. 背景マップとラベルの描画
    ax1.imshow(numeric_map, cmap=mcolors.ListedColormap(COLOR_LIST))
    labels_to_show = [
        (2, HEIGHT-2, "Entrance"), (2, 16, "Ticket"), (2, 8, "Queue"),
        (24, 3, "Kitchen"), (25, 20, "Tables")
    ] + [(lane, 5, f"C{i+1}") for i, lane in enumerate(ALL_LANES)]
    for lx, ly, text in labels_to_show:
        ax1.text(lx, ly, text, color="red", fontsize=10, ha="center", va="center", 
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1, alpha=0.8))
        
    # 2. ランダムに新しいグループを店内に投入
    if random.random() < 0.45:  
        group_size = random.randint(1, 4)  # 席が枯渇しすぎないよう最大人数を少し調整

        if len(SEATS) < group_size:
            continue
        
        new_group = Group(group_id=group_id_counter, size=group_size, base_duration=12)

        new_group.assigned_seats = []
        for _ in range(group_size):
            new_group.assigned_seats.append(SEATS.pop(0))

        all_groups.append(new_group)

        # メンバー生成
        for i in range(group_size):
            # メンバーごとに独立して役割を抽選（WAITINGが最多）
            role = random.choices(
                list(ROLE_WEIGHTS.keys()),
                weights=list(ROLE_WEIGHTS.values()),
                k=1
            )[0]
            # モバイル有効時：WAITINGの一部がMOBILEに置き換わる（WAITING↓ MOBILE↑）
            if MOBILE_ORDER_ENABLED and role == 'WAITING' and random.random() < MOBILE_ORDER_RATIO:
                role = 'MOBILE'
                
            new_agent = Agent(agent_id=agent_id_counter, role=role, group=new_group)

            if role == 'WAITING':
                new_agent.queue_index = len(ticket_queue)
                ticket_queue.append(new_agent)

            all_agents.append(new_agent)
            agent_id_counter += 1

        group_id_counter += 1

    # 3. 全エージェントの状態更新と描画
    active_count = 0
    for agent in all_agents:
        agent.update()
        if agent.x != -1 and agent.y != -1:
            active_count += 1
            color = {'WAITING': 'red', 'STAYER': 'purple', 'DIRECT': 'blue', 'MOBILE': 'green'}[agent.role]
            ax1.plot(agent.x, agent.y, marker='o', color=color, markersize=7, markeredgecolor='black', zorder=5)
            ax1.text(agent.x, agent.y - 1.2, f"{agent.role[0]}{agent.agent_id}", 
                    color="black", weight="bold", fontsize=6, ha="center")
    
    # 5step毎に今いる人数と平均不満度をプロット
    if step == 0 or step % 5 == 0:
        x_history.append(step)
        y_history.append(active_count)
        ax2.plot(x_history, y_history, color='forestgreen')
        ax2.set_xlabel("step")
        ax2.set_ylabel("user", color='forestgreen')
        ax2.set_title("statistics" , fontsize=14)

        # 不満度（開始からの累積平均）を右軸に赤で
        avg_d = (sum(d for _, d in satisfaction_log) / len(satisfaction_log)) if satisfaction_log else 0
        d_history.append(avg_d)
        ax2b.plot(x_history, d_history, color='crimson')
        ax2b.set_ylabel("dissatisfaction", color='crimson')
        ax2b.set_ylim(0, 100)

    # 4. 各グループのタイマー進行
    for group in all_groups:
        if group.timer_started and group.eating_duration > 0:
            group.eating_duration -= 1
    # 不満度表示
    avg_dissat = (sum(d for _, d in satisfaction_log) / len(satisfaction_log)) if satisfaction_log else 0
    per_role = []
    for r in ['WAITING', 'DIRECT', 'MOBILE']:
        vals = [d for role, d in satisfaction_log if role == r]
        if vals:
            per_role.append(f"{r[0]}:{sum(vals)/len(vals):.0f}")
    ax1.text(0.0, -0.13, f"avg dissatisfaction: {avg_dissat:.1f}", transform=ax1.transAxes, fontsize=9, color="dimgray", ha="left", va="top")
    ax1.text(0.0, -0.18, f"Active Guests: {active_count}", transform=ax1.transAxes, fontsize=9, color="dimgray", ha="left", va="top")

    ax1.text(0.5, -0.13, f"SEAT_RESTRICT: {SEAT_RESTRICT}", transform=ax1.transAxes, fontsize=9, color="dimgray", ha="left", va="top")  
    ax1.text(0.5, -0.18, f"MOBILE_ORDER: {MOBILE_ORDER_ENABLED}, RATIO: {MOBILE_ORDER_RATIO}", transform=ax1.transAxes, fontsize=9, color="dimgray", ha="left", va="top")

    ax1.set_title(f"Multi-Group Canteen Simulation - Step {step}" , fontsize=14)
    

    display.clear_output(wait=True)
    display.display(fig)
    plt.pause(0.1)

# 終了時：グラフ画像を保存してから閉じる
import os, datetime
os.makedirs("results", exist_ok=True)
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
mode = "mobileON" if MOBILE_ORDER_ENABLED else "mobileOFF"
base_path = os.path.join("results", f"sim_{stamp}_{mode}_{SEAT_RESTRICT}")
fig.savefig(base_path + ".png", dpi=120, bbox_inches="tight")
plt.close()

# ==========================================
# 4. 終了時の詳細データをファイルに書き出し
# ==========================================
import statistics, os, datetime

def _avg(vals):
    return f"{statistics.mean(vals):5.1f}" if vals else "  -  "

lines = []
def w(s=""):
    lines.append(s)

w("=" * 58)
w(" シミュレーション結果")
w("=" * 58)

# --- 条件 ---
w("[条件]")
w(f"  モバイルオーダー : {'ON' if MOBILE_ORDER_ENABLED else 'OFF'} (利用割合 {MOBILE_ORDER_RATIO})")
w(f"  席の時間制限     : {SEAT_RESTRICT}")
w(f"  受け取り口拡張   : {EXPAND_PICKUP_COUNTER}")
w(f"  総ステップ数     : {step}")

# --- 客数 ---
total_agents = len(all_agents)
served = [a for a in all_agents if a.dissatisfaction is not None]
unserved = total_agents - len(served)
w("")
w("[客数]")
w(f"  総グループ数     : {len(all_groups)}")
w(f"  総客数           : {total_agents}")
if total_agents:
    w(f"  食事到達         : {len(served)}  ({len(served) / total_agents * 100:.1f}%)")
    w(f"  未到達(滞留中)   : {unserved}")

# --- ロール別 ---
w("")
w("[ロール別]  (不満度・待ちは食事到達者のみ)")
w(f"  {'role':8s}{'num':>6s}{'share':>8s}{'dissat':>8s}{'wait_avg':>10s}{'wait_max':>10s}")
for r in ['WAITING', 'DIRECT', 'STAYER', 'MOBILE']:
    n = sum(1 for a in all_agents if a.role == r)
    if n == 0:
        continue
    dis = [a.dissatisfaction for a in served if a.role == r]
    wt = [a.wait_time for a in served if a.role == r]
    share = n / total_agents * 100 if total_agents else 0
    w(f"  {r:8s}{n:6d}{share:7.1f}%{_avg(dis):>8s}{_avg(wt):>10s}{(max(wt) if wt else 0):10d}")

# --- 全体 ---
all_dis = [a.dissatisfaction for a in served]
all_wt = [a.wait_time for a in served]
if all_dis:
    w("")
    w("[全体]")
    w(f"  平均不満度 : {statistics.mean(all_dis):.1f}   中央値 {statistics.median(all_dis):.1f}")
    w(f"  待ち時間   : 平均 {statistics.mean(all_wt):.1f} / 中央 {statistics.median(all_wt):.0f} / 最大 {max(all_wt)}")

w("=" * 58)

# --- ファイルへ書き出し（画像と同じ名前で対にする）---
out_path = base_path + ".txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"結果を {out_path} と {base_path}.png に保存しました")