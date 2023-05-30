'''
Author: ljf@2054316
Description: 
Date: 2023-01-17 21:54:17
LastEditTime: 2023-01-18 19:09:13
FilePath: \Project1\trial.py
'''
a={1:123,"1":123}

print(a)

print("{0}".format(True))

import threading
t=0
def fun():
  global t
  print(t)
  t+=1
  
t1=0
def fun1():
  global t1
  print(t1)
  t1+=1

class RepeatingTimer(threading.Timer):
        def run(self):
            while not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                self.finished.wait(self.interval)


t_check_dead = RepeatingTimer(1, fun)
t_check_dead.start()

t_check_dead2 = RepeatingTimer(1, fun1)
t_check_dead2.start()