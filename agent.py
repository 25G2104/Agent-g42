import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import datetime
import random
import os

#パラメータの定義
WIDTH = 80 #空間の幅
HEIGHT = 50 #空間の高さ
AGENTS_NUMBER = 300 #エージェントの数
CAPACITY = 200  #収容人数
SIMULATION_TIME = 200 #シミュレーション時間

#エージェントの種類
TYPE_WAITING = 0 #並ぶ人
TYPE_DIRECT = 1 #席に行く人
TYPE_STAYER = 2 #居座り続ける人

#エージェントの色分け
COLOR_WATING = 'red'
COLOR_DIRECT = 'blue'
COLOR_STAYER = 'green'

# 設備の配置座標
START_POS = (10.0, 0) #建物出入口
PARTITION_X = 20.0  #食堂仕切り壁のx位置
ENTRANCE_POS = (PARTITION_X, 40.0) #食堂入口
EXIT_POS = (PARTITION_X, 10.0) #食堂出口

TICKET_POS = [(1.0, 10.0 + i * 10) for i in range(4)] #券売機
COUNTER_POS = [(35.0 + i * 12, 49.0) for i in range(3)] #受け取りカウンター

SEAT_POS = [] #座席座標
cols = 30 # 横に並べる席数
x0, y0 = 25.0, 15.0 # 座席ブロックの左下の角
dx, dy = 1.5, 2.0 # 横・縦の間隔
for s in range(CAPACITY):
    sx = x0 + (s % cols) * dx
    sy = y0 + (s // cols) * dy
    SEAT_POS.append((sx, sy))

ENTRANCE_Y = (37.0, 43.0) # 壁の隙間のy範囲
EXIT_Y = (7.0, 13.0) # 壁の隙間のy範囲
WALLS = [
    # 外周
    ((80, 0), (80, 50)), # 右壁
    ((0, 0), (0, 50)), # 左壁
    ((0, 50), (80, 50)), # 上壁
    ((0, 0), (7, 0)), # 下壁（左）
    ((13, 0), (80, 0)), # 下壁（右）

    # 内部の壁
    ((PARTITION_X, ENTRANCE_Y[1]), (PARTITION_X, 50)), # 壁（上）
    ((PARTITION_X, ENTRANCE_Y[0]), (PARTITION_X, EXIT_Y[1])), # 壁（中）
    ((PARTITION_X, EXIT_Y[0]), (PARTITION_X, 0)), # 壁（下）
]

#エージェントのクラスの定義
class Agent:

    #グループ追加
    def __init__(self,agent_type, group_id, group_size):
        self.type = agent_type

        self.group_id = group_id #どのグループか
        self.group_size = group_size #グループの人数

        self.x = random.randint(0,WIDTH -1)
        self.y = random.randint(0,HEIGHT -1)

        #個体差
        self.speed = random.uniform(1.0,3.0) #速度
        self.stay_time = random.uniform(20,40) #滞在時間
        self.exit_time = random.uniform(3,10) #出る時間

        #状態
        self.stage = 0

    #行動の振り分け
    def update(self):
        if self.type == TYPE_WAITING:
            self.update_waiting()
        elif self.type == TYPE_DIRECT:
            self.update_direct()
        elif self.type == TYPE_STAYER:
            self.update_stayer()

   #振り分けされたエージェントがどのように動くか
    def update_waiting(self):
        pass
    def update_direct(self):
        pass
    def update_stayer(self):
        pass
    
#集団の生成と分類
agents = []
group_id = 0

while len(agents) < AGENTS_NUMBER:

    group_size = random.randint(1,5)
    group_agents = []

    #メンバー作成
    for i in range(group_size):
        agent = Agent(
            agent_type=None,
            group_id=group_id,
            group_size=group_size
        )
        group_agents.append(agent)
        agents.append(agent)

    #分類分け
    group_agents[0].type = TYPE_WAITING
    for a in group_agents[1:]:
        a.type = TYPE_DIRECT

    #居座りたい人を混ぜる
    for a in group_agents:
        if random.random() < 0.1:
            a.type = TYPE_STAYER

    group_id += 1

##MARK: 可視化
def visualize():
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.set_aspect('equal')
    #ax.grid(True)
    ax.set_title('Agent Simulation')

    #壁描画
    for (x1, y1), (x2, y2) in WALLS:
        ax.plot([x1, x2], [y1, y2], color='black', linewidth=2, solid_capstyle='round')
    # 設備描画
    def put(pos, label, marker='o', color='black', size=120):
        ax.scatter(pos[0], pos[1], marker=marker, c=color, s=size)
        ax.text(pos[0] + 0.7, pos[1] + 0.7, label, fontsize=6)

    put(START_POS, 'START', marker='*', color='black', size=150)
    put(ENTRANCE_POS, 'ENTRANCE', marker='', color='black', size=150)
    put(EXIT_POS, 'EXIT', marker='', color='black', size=150)
    for p in TICKET_POS:
        put(p, 'TICKET', marker='s', color='blue', size=150)
    for p in COUNTER_POS:
        put(p, 'COUNTER', marker='s', color='green', size=150)
    seat_x = [p[0] for p in SEAT_POS]
    seat_y = [p[1] for p in SEAT_POS]
    ax.scatter(seat_x, seat_y, marker='.', c='gray', s=20, label='SEAT')

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    visualize()
