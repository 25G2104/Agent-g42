import random
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from IPython import display

# ==========================================
# 条件設定
# ==========================================

# モバイルオーダー
MOBILE_ORDER_ENABLED = True
MOBILE_ORDER_RATIO = 0.5

wave_active = False
wave_end_step = 0

def arrival_probability(step):
    global wave_active, wave_end_step

    # 波が発生していないとき、ランダムに波を開始
    if not wave_active:
        if random.random() < 0.01:  # 1%の確率で波が始まる
            wave_active = True
            wave_end_step = step + random.randint(80, 200)
            print(f" Wave started! (step={step})")

    # 波が終了するタイミング
    if wave_active and step >= wave_end_step:
        wave_active = False
        print(f"Wave ended. (step={step})")

    # 波の間は高確率で入店
    if wave_active:
        return random.uniform(0.65, 0.85)

    # 波がないときは静か
    return random.uniform(0.05, 0.25)

SEAT_RESTRICT = 'SHORT'
EXPAND_TICKET_MACHINE = True
EXPAND_PICKUP_COUNTER = False

MENU_CURRY = 0
MENU_SETMEAL = 1
MENU_NOODLE = 2

if EXPAND_PICKUP_COUNTER:
    MENU_LANES = {MENU_CURRY: [12, 16], MENU_SETMEAL: [22, 26], MENU_NOODLE: [32, 36]}
else:
    MENU_LANES = {MENU_CURRY: [14], MENU_SETMEAL: [24], MENU_NOODLE: [34]}

if EXPAND_TICKET_MACHINE:
    TICKET_MACHINES = [(2, 12),(2,16), (2, 20), (2, 24)]  # 4台
else:
    TICKET_MACHINES = [(2, 12), (2, 16), (2, 20)]  # 3台（今まで通り）

ALL_LANES = [lane for lanes in MENU_LANES.values() for lane in lanes]
MOBILE_PICKUP_CAPACITY = len(ALL_LANES) * 3

# モバイル受け取り枠の上限（同時に取りに行ける人数）＝レーン数×3
MOBILE_PICKUP_CAPACITY = len(ALL_LANES) * 3

WAIT_TOLERANCE = 40
DISSAT_PER_STEP = 0.4
ROLE_WEIGHTS = {'WAITING': 70, 'DIRECT': 20, 'STAYER': 10}

# ==========================================
# レイアウト
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

# キッチン
for y in range(1, 5):
    for x in range(1, WIDTH-1):
        BASE_MAP[y][x] = "K"

# カウンター
for lane in ALL_LANES:
    BASE_MAP[5][lane] = "C"

# 返却口
for y in range(5, 8):
    for x in range(38, 42):
        BASE_MAP[y][x] = "H"

# 出入口
BASE_MAP[HEIGHT-1][2] = "D"

# 券売機
BASE_MAP[12][2] = "Y"
BASE_MAP[16][2] = "Y"
BASE_MAP[20][2] = "Y"

# 壁（席との境界）
for y in range(10, 21):
    BASE_MAP[y][9] = "W"

# 列スペース
for y in range(6, 26):
    for x in range(1, 4):
        BASE_MAP[y][x] = "Q"
    for x in range(5, 9):
        BASE_MAP[y][x] = "Q"

# カウンター列
for y in range(6, 13):
    for lane in ALL_LANES:
        BASE_MAP[y][lane] = "Q"

# 座席配置
SEATS = []
for y in range(16, 28, 3):
    for x in range(11, 42, 3):
        for dy in range(2):
            for dx in range(2):
                if BASE_MAP[y+dy][x+dx] == ".":
                    BASE_MAP[y+dy][x+dx] = "T"
                    SEATS.append((x+dx, y+dy))

SYMBOL_TO_INT = {".": 0, "W": 1, "D": 2, "Y": 3, "Q": 4, "C": 5, "K": 6, "T": 7, "H": 8}
COLOR_LIST = ["white", "black", "limegreen", "yellow", "skyblue", "orange", "darkgray", "peru", "mediumpurple"]
numeric_map = [[SYMBOL_TO_INT[cell] for cell in row] for row in BASE_MAP]

ENTRANCE = (2, HEIGHT-2)

# 券売機
for tx, ty in TICKET_MACHINES:
    BASE_MAP[ty][tx] = "Y"

COUNTERS = {menu: [(lane, 5) for lane in lanes] for menu, lanes in MENU_LANES.items()}

CORRIDOR_X = 6
WAITING_PASS_Y = 5
DIRECT_PASS_Y = 24

# ==========================================
# 列データ
# ==========================================
QUEUE_TICKET = [(2, y) for y in range(6, 26)]
ticket_queue = []

QUEUE_COUNTER = {lane: [(lane, y) for y in range(6, 26)] for lane in ALL_LANES}
counter_queues = {lane: [] for lane in ALL_LANES}

ticket_busy = [False] * len(TICKET_MACHINES)

counter_busy = {lane: False for lane in ALL_LANES}

mobile_ready = []
mobile_picking = [0]

satisfaction_log = []

def compute_dissatisfaction(wait):
    return min(100, max(0, (wait - WAIT_TOLERANCE) * DISSAT_PER_STEP))

# ==========================================
# グループとエージェント
# ==========================================
class Group:
    def __init__(self, group_id, size):
        self.group_id = group_id
        self.total_count = size
        self.seated_count = 0

        if SEAT_RESTRICT == 'NORMAL':
            self.eating_duration = random.randint(15, 25)
        elif SEAT_RESTRICT == 'SHORT':
            self.eating_duration = random.randint(10, 20)
        elif SEAT_RESTRICT == 'LONG':
            self.eating_duration = random.randint(20, 30)
        else:
            self.eating_duration = random.randint(10, 20)
        self.timer_started = False
        self.is_stayer_group = random.random() < 0.5
        self.assigned_seats = []


    def member_seated(self):
        self.seated_count += 1
        if self.seated_count == self.total_count:
            self.timer_started = True

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
        self.serve_timer = None
        self.wait_time = 0
        self.dissatisfaction = None
        self.menu = random.choice([MENU_CURRY, MENU_SETMEAL, MENU_NOODLE])
        self.speed = random.uniform(0.5, 1.5)

    def move_toward(self, tx, ty):
        if random.random ()> self.speed:
            return
        
        nx, ny = self.x, self.y
        if self.x < tx and BASE_MAP[self.y][self.x+1] != "W": nx += 1
        elif self.x > tx and BASE_MAP[self.y][self.x-1] != "W": nx -= 1
        if self.y < ty and BASE_MAP[self.y+1][self.x] != "W": ny += 1
        elif self.y > ty and BASE_MAP[self.y-1][self.x] != "W": ny -= 1
        self.x, self.y = nx, ny

    def generate_initial_path(self):
        # WAITING（赤）は券売機に行く前に席を確保する
        if self.role == 'WAITING':
            if self.group.assigned_seats:
                self.seat_xy = self.group.assigned_seats.pop(0)
            return

        # DIRECT は券売機をスキップしてカウンターへ直行 ★ 修正
        if self.role == 'DIRECT':
            if self.group.assigned_seats:
                self.seat_xy = self.group.assigned_seats.pop(0)
        
            candidates = MENU_LANES[self.menu]
            lane = min(candidates, key=lambda x: len(counter_queues[x]))
            self.counter_lane = lane
            self.queue_index = len(counter_queues[lane])
            counter_queues[lane].append(self)
            self.state = 'QUEUE_COUNTER'
            return
        
        #  STAYER は先に席を確保する
        if self.group.assigned_seats:
            self.seat_xy = self.group.assigned_seats.pop(0)

        # 初期移動ルート
        self.path.append((CORRIDOR_X, ENTRANCE[1]))
        self.path.append((CORRIDOR_X, DIRECT_PASS_Y))
        self.path.append((self.seat_xy[0], DIRECT_PASS_Y))
        self.path.append(self.seat_xy)
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
                tx, ty = QUEUE_TICKET[-1]

            if self.queue_index > 0:
                front = ticket_queue[self.queue_index - 1]
                if front.y < self.y - 1:
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

        # 2. 券売機へ
        if self.state == "BUY_TICKET":
            for i, (tx, ty) in enumerate(TICKET_MACHINES):
                if not ticket_busy[i]:
                    ticket_busy[i] = True
                    self.path = [(tx, ty)]
                    self.state = "TO_TICKET_MACHINE"

                    if ticket_queue and ticket_queue[0] == self:
                        ticket_queue.pop(0)
                        for j, ag in enumerate(ticket_queue):
                            ag.queue_index = j
                    return
            return

        # 3. 券売機前へ移動
        if self.state == "TO_TICKET_MACHINE":
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                for i, (tx, ty) in enumerate(TICKET_MACHINES):
                    if (self.x, self.y) == (tx, ty):
                        ticket_busy[i] = False

                candidates = MENU_LANES[self.menu]
                lane = min(candidates, key=lambda x: len(counter_queues[x]))
                self.counter_lane = lane
                self.queue_index = len(counter_queues[lane])
                counter_queues[lane].append(self)
                self.state = "QUEUE_COUNTER"
                return

         # 4. カウンター列
        if self.state == "QUEUE_COUNTER":
            lane = self.counter_lane
            queue = counter_queues[lane]
            path = QUEUE_COUNTER[lane]

            if self.queue_index < len(path):
                tx, ty = path[self.queue_index]
            else:
                tx, ty = path[-1]

            if (self.x, self.y) != (tx, ty):
                self.move_toward(tx, ty)
                return

            if self.queue_index == 0:
                self.state = "AT_COUNTER"
                return

        # 5. カウンター受け取り要求
        if self.state == "AT_COUNTER":
            lane = self.counter_lane
            queue = counter_queues[lane]
            if not counter_busy[lane]:
                counter_busy[lane] = True
                cx, cy = lane, 5

                if self.x < 9:  # 壁の左側にいる場合
                    self.path = [(CORRIDOR_X, self.y), (CORRIDOR_X, 5), (cx, cy)]
                else:
                    self.path = [(cx, cy)]

                self.state = "TO_COUNTER_SPOT"

                if queue and queue[0] == self:
                    counter_queues[lane].pop(0)
                    for j, ag in enumerate(counter_queues[lane]):
                        ag.queue_index = j
                return
            return

        # 6. カウンター前へ移動
        if self.state == "TO_COUNTER_SPOT":
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                if self.serve_timer is None:
                    self.serve_timer = random.randint(1, 5)
                if self.serve_timer > 0:
                    self.serve_timer -= 1
                    return

                counter_busy[self.counter_lane] = False
                self.serve_timer = None

                if self.role == 'MOBILE':
                    # モバイル客は席に戻るルートへ
                    self.path = [(self.seat_xy[0], WAITING_PASS_Y), self.seat_xy]
                    self.state = 'RETURN_TO_SEAT'
                else:
                    # 通常客は席へ移動する状態へ遷移
                    self.state = "PROCESS"
                return
            

        # 7. 席へ移動
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

                    if self.role == 'WAITING':
                        self.path = [
                            (CORRIDOR_X, ENTRANCE[1]),
                            (CORRIDOR_X, WAITING_PASS_Y),
                            (self.seat_xy[0], WAITING_PASS_Y),
                            self.seat_xy
                        ]
                    else:
                        self.path = [
                            (CORRIDOR_X, ENTRANCE[1]),
                            (CORRIDOR_X, DIRECT_PASS_Y),
                            (self.seat_xy[0], DIRECT_PASS_Y),
                            self.seat_xy
                        ]
                    return
                else:
                    return

            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
                
                return
            
            else:
                if self.role == 'MOBILE':
                    # モバイル客は席で通知待ち
                    self.state = 'MOBILE_WAITING'
                    self.notify_timer = random.randint(1, 5)  # 注文から調理完了まで
                else:
                    # 通常客はそのまま着席待ち
                    self.state = 'SEATED_WAITING'
                    self.group.member_seated()
                return
        
        #  席へ戻る(Waiting)
        if self.state == "RETURN_TO_SEAT":
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
                return
            else:
                self.state = "SEATED_WAITING"
                self.group.member_seated()
                return

        # MOBILE： 席で待ち、カウンター列へ合流
        if self.state == 'MOBILE_WAITING':
            # 調理完了通知のタイマー
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
                self.path = [(lane, WAITING_PASS_Y)]  # 受け取り口へ
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

        # 8. 食事開始
        if self.state == 'SEATED_WAITING':

            #グループの全員がそろったら食事
            if self.group.seated_count == self.group.total_count:
                self.state = 'EATING'
                self.dissatisfaction = compute_dissatisfaction(self.wait_time)
                satisfaction_log.append((self.role, self.dissatisfaction))
                return
            
        # 9. 食事中
        if self.state == 'EATING':
            self.group.eating_duration -= 1

            if self.group.eating_duration <= 0:
                if self.role == 'WAITING':
                    self.path = [(40, 6)]
                    self.state = 'TO_RETURN'
                elif self.role == 'DIRECT':  
                    self.path = [(40, 6)]
                    self.state = 'TO_RETURN'

                else:
                    self.path = [ENTRANCE]
                    self.state = 'LEAVE'

                if self.state == 'LEAVE' and not self.path:
                    if self.seat_xy:
                        SEATS.append(self.seat_xy)
                        self.seat_xy = None
                    self.x, self.y = -1, -1
                    return

        # 10. 返却口へ
        if self.state == 'TO_RETURN':
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                self.path = [ENTRANCE]
                self.state = 'LEAVE'
                return

        # 11. 退店
        if self.state == 'LEAVE':
            if self.path:
                tx, ty = self.path[0]
                self.move_toward(tx, ty)
                if (self.x, self.y) == (tx, ty):
                    self.path.pop(0)
            else:
                if self.seat_xy:
                    SEATS.append(self.seat_xy)
                    self.seat_xy = None
                self.x, self.y = -1, -1

# ==========================================
# シミュレーションと描画
# ==========================================
all_agents = []
all_groups = []
x_history = []
y_history = []
d_history = []

agent_id_counter = 1
group_id_counter = 101

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))
ax2b = ax2.twinx()

for step in range(1, 1201):
    ax1.clear()

    # 背景描画
    ax1.imshow(numeric_map, cmap=mcolors.ListedColormap(COLOR_LIST))

    # 新規グループ投入
    if random.random() < arrival_probability(step):
        group_size = random.randint(1, 4)
        if len(SEATS) < group_size:
            continue

        new_group = Group(group_id_counter, group_size)
        new_group.assigned_seats = [SEATS.pop(0) for _ in range(group_size)]
        all_groups.append(new_group)

        for _ in range(group_size):
            role = random.choices(list(ROLE_WEIGHTS.keys()), weights=list(ROLE_WEIGHTS.values()))[0]

            # モバイル有効時：WAITINGの一部がMOBILEに置き換わる
            if MOBILE_ORDER_ENABLED and role == 'WAITING' and random.random() < MOBILE_ORDER_RATIO:
                role = 'MOBILE'

            agent = Agent(agent_id_counter, role, new_group)
            agent.generate_initial_path()

            if role == 'WAITING':
                agent.queue_index = len(ticket_queue)
                ticket_queue.append(agent)

            all_agents.append(agent)
            agent_id_counter += 1

        group_id_counter += 1

    # エージェント更新
    active_count = 0
    for agent in all_agents:
        agent.update()
        if agent.x != -1:
            active_count += 1
            color = {'WAITING': 'red', 'STAYER': 'purple', 'DIRECT': 'blue', 'MOBILE': 'green'}[agent.role]
            ax1.plot(agent.x, agent.y, 'o', color=color, markersize=7)

    for tx, ty in TICKET_MACHINES:
        ax1.plot(tx, ty, marker='D', color='yellow', markersize=3)
    # グラフ更新
    if step % 5 == 0:
        x_history.append(step)
        y_history.append(active_count)
        ax2.plot(x_history, y_history, color='forestgreen')
        ax2.set_xlabel("step")
        ax2.set_ylabel("user")

        avg_d = (sum(d for _, d in satisfaction_log) / len(satisfaction_log)) if satisfaction_log else 0
        d_history.append(avg_d)
        ax2b.plot(x_history, d_history, color='crimson')
        ax2b.set_ylabel("dissatisfaction")
        ax2b.set_ylim(0, 100)

    display.clear_output(wait=True)
    display.display(fig)
    plt.pause(0.1)

plt.close()
