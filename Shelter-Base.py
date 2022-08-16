#!/usr/bin/env python
# coding: utf-8

#Author: Yaren Bilge Kaya, PhD Candidate in Industrial Engineering
#University: Northeastern University

from gurobipy import *
import gurobipy as gp
import pandas as pd
import numpy as np

import itertools
from pandas import ExcelWriter
from pandas import ExcelFile
import time


# Define the sets used in mathematical model:

################
##   Inputs   ##
################

#fixing random variables
np.random.seed(0) 

## Sets ##
Y= 500 #set of youth
S= 9 #set of shelters
Re=13 #set of refferal Organizations, 1 per each support service
Epsilon=3 # level of intensities
P= 13 #Number of services
I = 1+P*Epsilon #Total number of service intensity pairs (for brevity it's called services in the paper)
T=300 #set of days


## Youth and Shelter Profiles ##

# This part of the code extracts the youth and shelter characteristic (demographic) profiles
# as well as the information regarding the service requested and provided from respective excel files:

#Please keep in mind that the data gathered during this study is not going to be shared due to IRB restrictions;
# therefore the excel files are only included as placeholders as an example

#Characteristics Profiles

#YOUTH: Alpha matrix (youth charesteristics profiles)
df_alpha = pd.read_csv(r'/yarenbilgekaya/IISE-NYCShelterCapacityExpansionRevisions/alpha_y.csv')
df_alpha = df_alpha.iloc[:Y,1:]

#Youth or shelter attributes
N= len(df_alpha.columns)

#Youth characteristics profiles are created 
alpha_y =np.empty(shape=(Y,N))
for y in range(Y):
    for n in range(N):
        alpha_y[y,n]= int(df_alpha.iloc[y,n])

#ORGANIZATION: beta matrix (organization characteristics profiles)
df_beta = pd.read_csv(r'/yarenbilgekaya/IISE-NYCShelterCapacityExpansionRevisions/beta_s.csv')
df_beta = df_beta.iloc[:S+Re,1:]

#Organization characteristics profiles are created
beta_s =np.empty(shape=(S+Re,N))
for s in range(S+Re):
    for n in range(N):
        beta_s[s,n]= int(df_beta.iloc[s,n]) # assume all characteristics accepted by all referrals

#-----------------------------------------------------#

# Needs and Services lists 

# YOUTH: Needs matrix (youth needs profiles)
df_needs = pd.read_csv(r'/yarenbilgekaya/IISE-NYCShelterCapacityExpansionRevisions/needs_y_variation_1.csv')
df_needs = df_needs.iloc[:Y,1:]

#Needs of youth are created
needs_y ={}
for y in range(Y):
    for i in range(I):
        needs_y[y,i]= int(df_needs.iloc[y,i])
        
# ORGANIZATION: Services matrix (organization service profiles)       
df_services = pd.read_csv(r'/yarenbilgekaya/IISE-NYCShelterCapacityExpansionRevisions/services_s.csv')
df_services = df_services.iloc[:S+Re,1:]

#Shelter service profile (list of services provided by shelters) 
services_s =np.empty(shape=(S+Re,I))
for s in range(S+Re):
    for i in range(I):
        services_s[s,i]= int(df_services.iloc[s,i])         

# Now we specify youth's service time information from excel files, again these are only placeholders
# The below notation explains how we defined the parameters used in the model
# - duration ($d_{y,i}$)
# - frequency ($f_{y,i}$)
# - earliest service start time ($a_{y,i}$)
# - latest service start time ($b_{y,i}$)
# - arrival time ($l_{y}$)
# - time window flexibility parameter ($k_i$)

## Youth and time related parameters ##

#Service times for youth
df_times = pd.read_excel(r'/yarenbilgekaya/IISE-NYCShelterCapacityExpansionRevisions/times_yi.xlsx')
df_times = df_times.iloc[:Y*I,2:]

d_yi={} # duration of service
f_yi={} # number of times service is requested
a_yi={} # earliest start time of service
b_yi={} # latest start time of services

j=0
for y in range(Y):
    for i in range(I):
        d_yi[y,i]= int(df_times.iloc[j,0]) 
        f_yi[y,i]= int(df_times.iloc[j,1]) 
        a_yi[y,i]= int(df_times.iloc[j,2]) 
        b_yi[y,i]= int(df_times.iloc[j,3]) 
        j=j+1
        
#Arrival times for youth
df_arrival = pd.read_excel(r'//yarenbilgekaya/IISE-NYCShelterCapacityExpansionRevisions/arrival_y.xlsx')
df_arrival = df_arrival.iloc[:Y,1:]

l_y={} # arrival time of youth

j=0
for y in range(Y):
    l_y[y]= int(df_arrival.iloc[j]) 
    j=j+1
    
#flexibility of time window constraints for services
k_i={}
for y in range(Y):
    for i in range(I):
        if d_yi[y,i]>0:
            if d_yi[y,i]/f_yi[y,i]<3:
                k_i[i]=int(0)
            else:
                k_i[i]=int(1)
        else:
            k_i[i]=int(0)


# Shelter capacity and cost related parameters used in math model are given below:
# - capacity ($c_{s,i,t}$)
# - maximum amount of resource that you can accommodate in facility ($\mu_{s,i}$)
# - extra resource cost ($\gamma_{s,i}$)
# - overflow cost ($\lambda_{s,i}$})
# - assignment cost ($r_{y,s,i}$)

## Shelter and service related parameters ##

# Capacities
df_capacity = pd.read_excel(r'/yarenbilgekaya/IISE-NYCShelterCapacityExpansionRevisions/capacity_sit.xlsx')
df_capacity = df_capacity.iloc[:(S+Re)*I*T,3]

c_sit ={} # Capacity of the services at time t
j=0
for s in range(S+Re):
    for i in range(I):
        for t in range(T):
            c_sit[s,i,t]= int(df_capacity.iloc[j]) 
            j=j+1

#Costs            
df_costs = pd.read_excel(r'/yarenbilgekaya/IISE-NYCShelterCapacityExpansionRevisions/costs_si.xlsx')
df_costs= df_costs.iloc[:(S)*I,2:]

gamma_si = {} # Cost of adding additional resources
lambda_si = {} # Cost of sending youth to overflow shelters
mu_si ={} # Maximum number of resources that can be allocated to services
j=0
for s in range(S):
    for i in range(I):
        gamma_si[s,i]= int(df_costs.iloc[j,0]) 
        lambda_si[s,i] = int(df_costs.iloc[j,1]) 
        mu_si[s,i] = int(df_costs.iloc[j,2]) 
        j=j+1

#Cost of assigning youth
r_ysi = {}
for y in range(Y):
    for i in range(I):  
        for s in range(S):
            r_ysi[y,s,i] =int(0)
            if s==8:
                r_ysi[y,s,i] =int(100000)
        for s in range(S,S+Re):
            r_ysi[y,s,i] =int(20)


# The decision variables used in the model are given below:
# - youth to shelter assignment variable ($u_{y,s,i}$)
# - time dependent youth to shelter assignment variable ($x_{y,s,i}^t$)
# - extra resource decision variable ($e_{s,i}^t$)
# - overflow decision variable ($o_{s,i}^t$)

print(f"\n-------------------------------------------------------------------------------------------") 
print(f"Code is running with {Y} youths, {S} shelters, {Re} referrals, {I} services and for {T} days.")
print(f"\n-------------------------------------------------------------------------------------------") 

############
#  Model   #
############

#Define time stamp and initial number of total decision variables
tic_dec = time.perf_counter()
no_dec_vars =0

m = Model("Capacity_Expansion_TIL_Base1")

################
#  Variables   #
################

#Extra resource decison variables project the number of requied extra resources for each service
#first component represents the shelter (s), second component the service (i), and third is  the time (t)
e ={}
for s in range(S):
    for i in range(I):
        for t in range(T):
            if c_sit[s,i,t]>0: 
                e[s,i,t] = m.addVar(vtype=GRB.CONTINUOUS, name= 'e('+str(s)+','+str(i)+','+str(t)+')')
                no_dec_vars = no_dec_vars +1

#Overflow decision variable projects the number of youth that needs to be sent to the overflow shelters
#first component represents the shelter (s), second component the service (i), and third is  the time (t)
o ={}
for s in range(S):
    for i in range(I):
        for t in range(T):
            if c_sit[s,i,t]>0: 
                o[s,i,t] = m.addVar(vtype=GRB.CONTINUOUS, name= 'o('+str(s)+','+str(i)+','+str(t)+')')
                no_dec_vars = no_dec_vars +1

#Time dependent youth to shelter assignment decision variable:
#shows whether a youth is assigned to a shelter s, to receive service i, at time t
#first component represents the youth (y), second component the shelter (s), third is the service (i), and forth the time (t)
x ={}
for y in range(Y):
    for s in range(S+Re):
        for i in range(I):
            for t in range(T):
                if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) and t<(b_yi[y,i]+d_yi[y,i]+2) : 
                    x[y,s,i,t] = m.addVar(vtype=GRB.BINARY, name= 'x('+str(y)+','+str(s)+','+str(i)+','+str(t)+')') 
                    no_dec_vars = no_dec_vars +1

#Youth to shelter assignment decision varible
#first component represents the youth (y), second component the shelter (s), third is the service (i)
u = {}
for y in range(Y):
    for s in range(S+Re):
        for i in range(I):
            if d_yi[y,i]>0: 
                u[y,s,i] = m.addVar(vtype=GRB.BINARY, name= 'u('+str(y)+','+str(s)+','+str(i)+')')
                no_dec_vars = no_dec_vars +1
        
m.update()

toc_dec=time.perf_counter()

print('There are '+str(no_dec_vars)+' in the system rather than ' +str(Y*(S+Re)*I*T))

print(f"\n-----------------------------------------------------")
print(f"Building the decision variables takes {toc_dec - tic_dec:0.4f} seconds")
print(f"\n-----------------------------------------------------")


# The objective function is given below: (summation of associated costs)

tic_obj = time.perf_counter()

################
#  Objective   #
################

#Functions to define the objective
def AssignmentCost(x):
    assignment_cost = 0
    for y in range(Y):
        for s in range(S+Re):
            for i in range(I):
                for t in range(T):
                    if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) and t<(b_yi[y,i]+d_yi[y,i]+2) : 
                        assignment_cost = assignment_cost + r_ysi[y,s,i]*x[y,s,i,t]
    return assignment_cost

def ResourceCost(e):
    resource_cost = 0
    for s in range(S):
        for i in range(I):
            for t in range(T):
                if c_sit[s,i,t]>0: 
                        resource_cost = resource_cost + gamma_si[s,i]*e[s,i,t]
    return resource_cost

def OverflowCost(o):
    overflow_cost = 0
    for s in range(S):
        for i in range(I):
            for t in range(T):
                if c_sit[s,i,t]>0 : 
                        overflow_cost = overflow_cost + lambda_si[s,i]*o[s,i,t]
    return overflow_cost

#objective function: sum of cost of adding extra resources and cost of assigning youth
m.setObjective(AssignmentCost(x) + ResourceCost(e)+ OverflowCost(o), GRB.MINIMIZE)
m.update()

toc_obj=time.perf_counter()

print(f"\n-----------------------------------------------------")
print(f"Building the objective function takes {toc_obj - tic_obj:0.4f} seconds")
print(f"\n-----------------------------------------------------")


# Constraint are given below:

#Initialize the time stamp and the number of constraints in the model
tic_cons = time.perf_counter()
no_of_constraints =0

#################
#  Constraints  #
#################

#1: Capacity of service i in shelter s should not be exceeded. 
for s in range(S):
    for i in range(I):
        for t in range(T):
            if c_sit[s,i,t]>0:
                m.addConstr(sum(x[y,s,i,t] for y in range(Y) if d_yi[y,i]>0 and (t>l_y[y]-2) 
                                and t<(b_yi[y,i]+d_yi[y,i]+2))-e[s,i,t] -o[s,i,t] <= c_sit[s,i,t], 
                        name='capacity_const'+str(s)+','+str(i)+','+str(t))  
                no_of_constraints = no_of_constraints +1

#2:There is a maximum amount of resources that service providers can have within their facilities
for s in range(S):
    for i in range(I):
        for t in range(T):
            if c_sit[s,i,t]>0:
                m.addConstr(c_sit[s,i,t]+ e[s,i,t]  <= mu_si[s,i], name='at_most'+str(s)+','+str(i)+','+str(t))  
                no_of_constraints = no_of_constraints +1


#3: Each youth should only be placed on one shelter at time t. 
for y in range(Y):
    for i in range(I):
        if d_yi[y,i]>0:
            m.addConstr(sum(u[y,s,i] for s in range(S+Re) if d_yi[y,i]>0 and c_sit[s,i,t]>0) <= 1,
                        name='single_shelter_const'+str(y)+','+str(i))
            no_of_constraints = no_of_constraints +1
            
                
#4: if youth can receive a service from only one service provider, they should be assigned 
# to that service provider for the amount of time they need the service
for y in range(Y):
    for s in range(S+Re):
        for i in range(I):
            if d_yi[y,i]>0:
                m.addConstr(sum(x[y,s,i,t] for t in range(T) if c_sit[s,i,t]>0 and (t>l_y[y]-2) and t<(b_yi[y,i]+d_yi[y,i]+2))
                            <= T*u[y,s,i], name='all_to_one_shelter'','+str(y)+','+str(s)+','+str(i))
                no_of_constraints = no_of_constraints +1
                
#5 : If youth has a bed in a shelter, they should get all the services from that one          
for y in range(Y):
    if d_yi[y,0]>0:
        for i in range(I):
            for s in range(S):
                shelterlist = [j for j in range(0,S)]
                shelterlist.remove(s)
                shelterlist.sort()
                if d_yi[y,i]>0:
                  m.addGenConstrIndicator(u[y,s,0], True, sum(u[y,j,i] for j in shelterlist), GRB.EQUAL, 0.0,
                                name='shelter_const'+str(y)+','+str(i)+','+str(s))
                  no_of_constraints = no_of_constraints +1
                    
#6.1: If the service is NOT PERIODICAL, 
#this constraint makes sure that it's served to youth within youth's stay and is equal to the time it's needed
list_nonperiod = [1,4,5,6,7,8,10,11,16,17,19,20,21,28,29,30,31,33,34]
for y in range(Y):
    for i in list_nonperiod:
        if d_yi[y,i]>0:
            m.addConstr(sum(x[y,s,i,t] for t in range(b_yi[y,i]+d_yi[y,i]) for s in range(S+Re) 
                                                      if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) 
                                and t<(b_yi[y,i]+d_yi[y,i]+2)) == f_yi[y,i], 
                        name='non_period_dur_const'+str(y)+','+str(i))
            no_of_constraints = no_of_constraints +1


#6.2: If the service is PERIODICAL, 
#this constraint makes sure that it's served to youth within youth's stay and is equal to the time it's needed
list_period = [0,2,3,9,12,13,14,15,18,22,23,24,25,26,27,32,35,36,37,38]
for y in range(Y):
    for i in list_period:
        if d_yi[y,i]>0: 
            #define teh periodicity
            period = math.floor(d_yi[y,i]/f_yi[y,i])
            if k_i[i]==0:
                m.addConstr(sum(x[y,s,i,t] for t in range(0,b_yi[y,i]+d_yi[y,i], period) for s in range(S+Re)
                               if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) and t<(b_yi[y,i]+d_yi[y,i]+2)) == f_yi[y,i], 
                            name='period_dur_const'+str(y)+','+str(i))
                no_of_constraints = no_of_constraints +1
            else:
                if period>3:
                    m.addConstr(sum(x[y,s,i,t+k] for t in range(l_y[y],b_yi[y,i]+d_yi[y,i], period) for k in range(-k_i[i],k_i[i])
                                for s in range(S+Re) if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) 
                                and t<(b_yi[y,i]+d_yi[y,i]+2) ) == f_yi[y,i], name='period_dur_const'+str(y)+','+str(i))
                    no_of_constraints = no_of_constraints +1
            #7: When we add flexibility sum over that time should be equal to 1
                    for t in range(l_y[y],b_yi[y,i]+d_yi[y,i], period):
                        m.addConstr(sum(x[y,s,i,t+k] for k in range(-k_i[i],k_i[i]) for s in range(S+Re)
                                        if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) and t<(b_yi[y,i]+d_yi[y,i]+2))<= 1, 
                                    name='flexibility'+str(y)+','+str(s)+','+str(i)+','+str(t))
                        no_of_constraints = no_of_constraints +1
            
        
                    
#8: The first time service is provided shouln't be before the earliest time 
# and service shouldn't be provided after the latest time+duration
for y in range(Y):
    for i in range(I):
        if d_yi[y,i]>0:
            m.addConstr(sum(x[y,s,i,t] for s in range(S+Re) for t in range(0,a_yi[y,i]) 
                           if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) 
                            and t<(b_yi[y,i]+d_yi[y,i]+2)) ==0, name='no_before'+str(y)+','+str(i))
            m.addConstr(sum(x[y,s,i,t] for s in range(S+Re) for t in range(b_yi[y,i]+d_yi[y,i],T) 
                           if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) 
                                and t<(b_yi[y,i]+d_yi[y,i]+2))==0, name='no_after'+str(y)+','+str(i))
            no_of_constraints = no_of_constraints +2

#9: The first time service should be provided between the time window
for y in range(Y):
    for i in range(I):
        if d_yi[y,i]>0 :
            m.addConstr(sum(x[y,s,i,t] for t in range(a_yi[y,i], b_yi[y,i]) for s in range(S+Re)
                           if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) and t<(b_yi[y,i]+d_yi[y,i]+2)) >=1 ,
                        name='time_window_const'+str(y)+','+str(i)) 
            no_of_constraints = no_of_constraints +1
                                 
#10: If youth's profile does not match with the service provider profile they shouldn't be matched.
for y in range(Y):
    alpha_1s=alpha_y[y,:].nonzero()
    alpha_1s= alpha_1s[0]
    for s in range(S+Re):
        for n in alpha_1s:
            if beta_s[s,n]==0:
                for i in range(I):
                    for t in range(T):
                        if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]-2) and t<(b_yi[y,i]+d_yi[y,i]+2):
                            m.addConstr(x[y,s,i,t] == 0, name= 'profile_match'+str(y)+','+str(s)+','+str(i)+','+str(t))
                            no_of_constraints = no_of_constraints +1

m.update()

toc_cons=time.perf_counter()

print('There are ' +str(no_of_constraints) + ' constraints in the system')

print(f"\n-----------------------------------------------------")
print(f"Building the constraints takes {toc_cons - tic_cons:0.4f} seconds")
print(f"\n-----------------------------------------------------")


# In[ ]:


####################
#   Optimization   #
####################

m.Params.MIPGap = 0.01 #Define MIP Gap
#m.Params.TimeLimit = 60*10 #Define Time Limit in seconds

tic_opt = time.perf_counter()
m.write(r'<your directory>/Shelter-TIL.lp')

# Run optimization engine
m.optimize()

toc_opt = time.perf_counter()
print(f"\n-----------------------------------------------------")
print(f"Optimization took {toc_opt - tic_opt:0.4f} seconds")
print(f"\n-----------------------------------------------------")

#Prints decision variables and costs into an excel file
#decision variables
varInfo = [(v.varName, v.X) for v in m.getVars() if v.X > 0]
obj = m.getObjective()

dec_variables = pd.DataFrame(varInfo, columns = ['Dec Variable','Value'])

obj = m.getObjective()
obj_value= obj.getValue()

T=180

#Assignment cost to referrals

count1 =0
for y in range(Y):
    for s in range(S,S+Re):
        for i in range(I):
            for t in range(T):
                if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]) and t<(b_yi[y,i]+d_yi[y,i]+1):
                    if x[y,s,i,t].x>0:
                        count1= count1+1
print('Assignment cost to referrals is: $' +str(count1*r_ysi[0,S+5,9]))

#Assignment cost to dummy organization
count2 =0
s=8
for y in range(Y):
    for i in range(I):
        for t in range(T):
            if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]) and t<(b_yi[y,i]+d_yi[y,i]+1):
                if x[y,s,i,t].x>0:
                    count2= count2+1
print('Assignment cost to dummy organization is: $' +str(count2*r_ysi[0,8,0]))


#Cost of adding extra resources
resource_cost = 0
for s in range(S):
    for i in range(I):
        for t in range(T):
            if c_sit[s,i,t]>0: 
                resource_cost = resource_cost + gamma_si[s,i]*e[s,i,t].x
print('Adding extra resources to organizations cost: $' +str(resource_cost))

#Cost of sending youth to overflow shelters
overflow_cost = 0
for s in range(S):
    for i in range(I):
        for t in range(T):
            if c_sit[s,i,t]>0 : 
                overflow_cost = overflow_cost + lambda_si[s,i]*o[s,i,t].x
print('Sending youth to overflow shelters cost: $' +str(overflow_cost))

array = np.array([obj_value, count2*r_ysi[0,15,0], count1*r_ysi[0,S+5,9], resource_cost, 
                  overflow_cost, (overflow_cost+resource_cost+count1*r_ysi[0,S+5,9]+count2*r_ysi[0,15,0]) ] )
costs = pd.DataFrame(array, columns= ['Values'], index = ['objective', 'Assignment cost to incompatibility', 'Assignment cost to referrals', 
                           'Adding extra resources in house', 'Overflow', 'Total'])

writer = ExcelWriter(r'<your directory>/Shelter-Variables.xlsx')
dec_variables.to_excel(writer, sheet_name='Variables')
costs.to_excel(writer, sheet_name='Costs')
writer.save() 


## Outputs in Excel Files ##  

T=180

as_decision= [0 for i in range(8)]
list_t =[]
for y in range(Y):
    for s in range(S+Re):
        for i in range(I):
            for t in range(T):
                if d_yi[y,i]>0 and c_sit[s,i,t]>0 and (t>l_y[y]) and t<(b_yi[y,i]+d_yi[y,i]+1) :
                    if x[y,s,i,t].x >0:
                        list_t.append(t)
            if len(list_t)>0:
                as_decision = np.vstack([as_decision, [d_yi[y,i], f_yi[y,i], a_yi[y,i], b_yi[y,i], y,s,i,list_t]])
            list_t =[]  

as_decision=np.delete(as_decision, 0, 0)
df_assignment = pd.DataFrame(as_decision, columns = ['Duration', 'Frequency','Earliest','Latest','Youth','Organization','Service','Days'])
writer = ExcelWriter(r'<your directory>/ShelterAssignment.xlsx')
df_assignment.to_excel(writer,'Assignments',index=False)
writer.save()       


res_decision= [0 for i in range(4)]
extra_total_resource =0
for s in range(S):
    for i in range(I):
        for t in range(T):
            if c_sit[s,i,t]>0:
                tmp1= e[s,i,t].x 
                if tmp1 >0:
                    res_decision = np.vstack([res_decision, [s,i,t,tmp1]])

res_decision=np.delete(res_decision, 0, 0)

if len(res_decision) <=4:
    print('Extra resource array is empty')
else:
    df_resources = pd.DataFrame(res_decision, columns = ['Organization','Service','Day','Extra Resources'])
    writer = ExcelWriter(r'<your directory>/ShelterExtraResources.xlsx')
    df_resources.to_excel(writer,'Resources',index=False)
    writer.save()   

overflow_decision= [0 for i in range(4)]
for s in range(S):
    for i in range(I):
        for t in range(T):
            if c_sit[s,i,t]>0:
                tmp1= o[s,i,t].x 
                if tmp1 >0:
                    overflow_decision = np.vstack([overflow_decision, [s,i,t,tmp1]])

overflow_decision=np.delete(overflow_decision, 0, 0)

if len(overflow_decision) <=4:
    print('Overflow array is empty')
else:
    df_overflow = pd.DataFrame(overflow_decision, columns = ['Organization','Service','Day','# of overflows'])
    writer = ExcelWriter(r'<your directory>/ShelterOverflow.xlsx')
    df_overflow.to_excel(writer,'Overflow',index=False)
    writer.save()   

print('=============================================================')
print('________________ Excel file(s) are produced___________________')
print('=============================================================')


#Only run this part and below if it's infeasible to see the conflicting constraints
#Computing an Irreducible Inconsistent Subsystem (IIS)

status = m.status
if status == GRB.UNBOUNDED:
    print('The model cannot be solved because it is unbounded')
    sys.exit(0)
if status == GRB.OPTIMAL:
    print('The optimal objective is %g' % m.objVal)
    sys.exit(0)
if status != GRB.INF_OR_UNBD and status != GRB.INFEASIBLE:
    print('Optimization was stopped with status %d' % status)
    sys.exit(0)

# do IIS
print('The model is infeasible; computing IIS')
removed = []

# Loop until we reduce to a model that can be solved
while True:

    m.computeIIS()
    print('\nThe following constraint cannot be satisfied:')
    for c in m.getConstrs():
        if c.IISConstr:
            print('%s' % c.constrName)
            # Remove a single constraint from the model
            removed.append(str(c.constrName))
            m.remove(c)
            break
    print('')

    m.optimize()
    status = m.status

    if status == GRB.UNBOUNDED:
        print('The model cannot be solved because it is unbounded')
        sys.exit(0)
    if status == GRB.OPTIMAL:
        break
    if status != GRB.INF_OR_UNBD and status != GRB.INFEASIBLE:
        print('Optimization was stopped with status %d' % status)
        sys.exit(0)

print('\nThe following constraints were removed to get a feasible LP:')
print(removed)

