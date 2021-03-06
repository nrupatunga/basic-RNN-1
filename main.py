#Toy example of seq2seq modeling using vanilla RNN 
# h(t) = tanh(Wxh*x(t) + Whh*h(t-1) + bh)
# y(t) = Wyh*h(t) + by 
# x(t) is n dimensional embedding for one hot vector for vocabulary of length m 

import numpy as np
import os
import sys
import pdb
from random import uniform

class VanillaRNN:

  def __init__(self,txtFile,num_hidden_units,seq_len,learning_rate,num_epochs):
    f = open(txtFile,'r')
    self.data = f.read()
    chars = list(set(self.data))
    num_data = len(self.data)
    num_chars = len(chars) 
    self.char_to_index = {c:i for i,c in enumerate(chars)}
    self.index_to_char = {i:c for i,c in enumerate(chars)}
    self.num_hidden_units = num_hidden_units
    self.vocab_size = num_chars
    self.whh = np.random.randn(num_hidden_units,num_hidden_units)*0.01
    self.wxh = np.random.randn(num_hidden_units,self.vocab_size)*0.01
    self.wyh = np.random.randn(self.vocab_size,num_hidden_units)*0.01
    self.bh = np.zeros((num_hidden_units,1))
    self.by = np.zeros((self.vocab_size,1))
    self.seq_len = seq_len
    self.learning_rate = learning_rate
    self.num_epochs = num_epochs 

  def forward(self,inputs,hprev):

    x = {}
    h1 = {}
    probs = {}

    h1[-1] = np.copy(hprev)
 
    for i in range(seq_len):
      x[i] = np.zeros((self.vocab_size,1))
      x[i][inputs[i]] = 1
      
      h1[i] = np.dot(self.wxh , x[i]) + np.dot(self.whh , h1[i-1]) + self.bh 
      h1[i] = np.tanh(h1[i])
      logits = np.dot(self.wyh, h1[i]) + self.by
      #pdb.set_trace()
      probs[i] = np.exp(logits)/sum(np.exp(logits))

    return x,h1,probs,h1[seq_len-1]


  def loss(self,probs,targets):
    loss = 0
    for i in range(self.seq_len):
      loss += -np.log(probs[i][targets[i]])
    return loss


  def backward(self,probs,targets,x,h1):
    dh_next = np.zeros_like(h1[0])
    dyh = np.zeros_like(self.wyh)
    dxh = np.zeros_like(self.wxh)
    dhh = np.zeros_like(self.whh)
    dbh = np.zeros_like(self.bh)
    dby = np.zeros_like(self.by)
    dh = np.zeros_like(h1[0])

    for i in reversed(range(len(targets))):
      dy = np.copy(probs[i])
      dy[targets[i]] -= 1    

      #backpropogate to wyh 
      dyh += np.dot(dy,h1[i].T)
      dby += dy     

      #backpropogate to h 
      dh = np.dot(self.wyh.T,dy) + dh_next
      

      #backpropogate to h before non-linearity
      dh_bef = dh*(1-(h1[i]*h1[i]))      
      dbh += dh_bef

      #backpropogate to wxh
      dxh += np.dot(dh_bef,x[i].T)

      #backpropogate to whh 
      dhh += np.dot(dh_bef,h1[i-1].T)

      dh_next = np.dot(self.whh.T,dh_bef)

    return dxh,dhh,dyh,dbh,dby

  def SGD_step(self,dxh,dhh,dyh,dbh,dby):
    
    np.clip(dxh,-5,5,out=dxh)
    np.clip(dhh,-5,5,out=dhh)
    np.clip(dyh,-5,5,out=dyh)
    self.wxh -= self.learning_rate*dxh
    self.whh -= self.learning_rate*dhh
    self.wyh -= self.learning_rate*dyh
    self.bh  -= self.learning_rate*dbh
    self.by  -= self.learning_rate*dby

  def sample(self,start,hprev,num_chars):
    start_idx = start

    #h = np.zeros((self.num_hidden_units,1))
    idx = start_idx
    seq = [self.index_to_char[start]]    

    for i in range(num_chars):
      x = np.zeros((self.vocab_size,1))
      x[idx] = 1
      h1 = np.dot(self.wxh , x) + np.dot(self.whh , hprev) + self.bh
      h1 = np.tanh(h1)
      logits = np.dot(self.wyh, h1) + self.by
      probs = np.exp(logits)/sum(np.exp(logits))
      hprev = np.copy(h1)
      idx = np.random.choice(range(self.vocab_size),p=probs.ravel())
      seq.append(self.index_to_char[idx])

    return seq

  #Gradient check code from Andrej Karpathy 

  def gradCheck(self,inputs, target, hprev):

    global Wxh, Whh, Why, bh, by
    num_checks, delta = 10, 1e-5
    x,h1,probs,hprev = self.forward(inputs,hprev)
    dwxh,dwhh,dwyh,dbh,dby = self.backward(probs,target,x,h1)    

    for param,dparam,name in zip([self.wxh, self.whh, self.wyh, self.bh, self.by], [dwxh, dwhh, dwyh, dbh, dby], ['Wxh', 'Whh', 'Why', 'bh', 'by']):
      s0 = dparam.shape
      s1 = param.shape
      assert s0 == s1, 'Error dims dont match: %s and %s.' % (`s0`, `s1`)
      print name

      for i in xrange(num_checks):
        ri = int(uniform(0,param.size))
        # evaluate cost at [x + delta] and [x - delta]
        old_val = param.flat[ri]
        param.flat[ri] = old_val + delta
       
        x,h1,probs,hprev = self.forward(inputs,hprev)
        cg0 = self.loss(probs,target)

        param.flat[ri] = old_val - delta
        
        x,h1,probs,hprev = self.forward(inputs,hprev)
        cg1 = self.loss(probs,target)
        
        param.flat[ri] = old_val # reset old value for this parameter
        # fetch both numerical and analytic gradient
        grad_analytic = dparam.flat[ri]
        grad_numerical = (cg0 - cg1) / ( 2 * delta )
        rel_error = abs(grad_analytic - grad_numerical) / abs(grad_numerical + grad_analytic)
        print '%f, %f => %e ' % (grad_numerical, grad_analytic, rel_error)
        # rel_error should be on order of 1e-7 or less


 
txtFile = sys.argv[1] 
num_hidden_units = 100
seq_len = 25 
rnn = VanillaRNN(txtFile,num_hidden_units,seq_len,0.01,10)

hprev = np.zeros((rnn.num_hidden_units,1))


inputs = [rnn.char_to_index[ch] for ch in rnn.data[0*rnn.seq_len:(0+1)*rnn.seq_len]]
outputs= [rnn.char_to_index[ch] for ch in rnn.data[0*rnn.seq_len + 1:(0+1)*rnn.seq_len + 1]]
rnn.gradCheck(inputs,outputs,hprev)
pdb.set_trace()


count = 0

for j in range(rnn.num_epochs):
  
  for i in range(len(rnn.data)/rnn.seq_len):

    if i == 0:
      hprev = np.zeros((rnn.num_hidden_units,1))

    inputs = [rnn.char_to_index[ch] for ch in rnn.data[i*rnn.seq_len:(i+1)*rnn.seq_len]]
    outputs= [rnn.char_to_index[ch] for ch in rnn.data[i*rnn.seq_len + 1:(i+1)*rnn.seq_len + 1]]

    x,h1,probs,hprev = rnn.forward(inputs,hprev)
    loss = rnn.loss(probs,outputs)
    

    dwxh,dwhh,dwyh,dbh,dby = rnn.backward(probs,outputs,x,h1)
    rnn.SGD_step(dwxh,dwhh,dwyh,dbh,dby)
    #pdb.set_trace()
    #print count
 
    if count%100 == 0:
      
      seq = rnn.sample(inputs[0],hprev,50) 
      txt = ''.join(ix for ix in seq)
      print txt
    count += 1





    
    
