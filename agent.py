import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import datetime
import random
import os

#パラメータの定義
WIDTH = 50 #空間の幅
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

#エージェントのクラスの定義
class Agent:

    def __init__(self,agent_type):
        self.type = agent_type
        self.x = random.randint(0,WIDTH -1)
        self.y = random.randint(0,HEIGHT -1)

        #個体差
        self.speed = random.uniform(1.0,3.0)
        self.stay_time = random.uniform(20,40)
        self.exit_time = random.uniform(3,10)

        #状態
        self.stage = 0


    def update(self):
        if self.type == TYPE_WAITING:
            self.update_waiting()
        elif self.type == TYPE_DIRECT:
            self.update_direct()
        elif self.type == TYPE_STAYER:
            self.update_stayer()

    def update_waiting(self):

    def update_direct(self):

    def update_stayer(self):