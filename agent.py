import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import datetime
import random
import os

#パラメータの定義
WIDTH = 50 #空間の幅
HEIGHT = 50 #空間の高さ

# 席の右上、左下の座標をタプルで指定、矩形で囲んで領域とする。
SEAT_START = (,) # 席の領域の右上の座標(x,y)
SEAT_END = (,)   # 席の領域の左下の座標(x,y)
SEAT_CENTER = ((SEAT_END[0]-SEAT_START[0])/2,(SEAT_END[1]-SEAT_START[1])/2) # 席の領域の中央点

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

    def update_direct(self):

    def update_stayer(self):
        # エージェントが"席に行く人"の状態だった場合、席の座標に移動して静止する。
        if agent.type == TYPE_STAYER:
            # 席に着くまでずっと移動する。
            while(not(SEAT_START[0] <= self.x <= SEAT_END[0]) and (SEAT_START[1] <= self.y <= SEAT_END[1])):
                self = np.random.rand() * 2 * np.pi    # 席のある領域の中央へ向かうように角度を設定
                self.x += AGENT_SPEED * np.cos(angle)  # x座標更新
                self.y += AGENT_SPEED * np.sin(angle)  # y座標更新
                self.x = max(0, min(self.x, WIDTH))    # 席の領域内に収まるように調整
                self.y = max(0, min(self.y, HEIGHT))   # 席の領域内に収まるように調整
