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