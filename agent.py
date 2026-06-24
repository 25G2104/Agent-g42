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
START_POS = (10.0, 0) #建物入口
ENTRANCE_POS = (20.0, 40) #食堂入口
EXIT_POS = (20.0, 10.0) #食堂出口

TICKET_POS = [(1.0, 10.0 + i * 10) for i in range(4)] 
COUNTER_POS = [(35.0 + i * 12, 49.0) for i in range(3)]

#エージェントのクラスの定義
class Agent:

    def __init__(self,agent_type):
        self.type = agent_type
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



def visualize():
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.set_aspect('equal')
    ax.grid(True)
    ax.set_title('Agent Simulation')

    # --- 1点の座標（タプル）を置いて、名前ラベルを付ける ---
    def put(pos, label, marker='o', color='black', size=120):
        ax.scatter(pos[0], pos[1], marker=marker, c=color, s=size)
        ax.text(pos[0] + 0.7, pos[1] + 0.7, label, fontsize=6)

    put(START_POS, 'START', marker='*', color='black', size=150)
    put(ENTRANCE_POS, 'ENTRANCE', marker='*', color='black', size=150)
    put(EXIT_POS, 'EXIT', marker='*', color='black', size=150)
    for p in TICKET_POS:
        put(p, 'TICKET', marker='s', color='blue', size=150)
    for p in COUNTER_POS:
        put(p, 'COUNTER', marker='s', color='green', size=150)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    visualize()
