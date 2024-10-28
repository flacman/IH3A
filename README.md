# IH3A

The whole system is composed by 3 sections:

## IH3A Agent:
Intelligent Hacking Auto Attacking Agent: In charge of dealing with the attacks an learning.\
    This agent will try an attack based on pre-defined parameters and track messages from the RLHelper. When a signal is received, it means the defender busted the agent, and he'll need to adjust its attacking parameters.\
    The training score will be decided based on 3 metrics:\
    \
    1. How many *attacks* he was able to perform before getting busted\
    2. The attack was successful?\
    3. Lenght of the attack. If it surpasses a threashold, it will be understanded by a failure (e.g: we don't want the attack to last a year)\
    After proper training, it is expeted to deliver a version of the parameters needed to avoid the defendant infraestructure\
    \
    **Challenges:**\
    Build a mechanism that allow the agent to learn quickly. As in RL we need a lot of data, each iteration could last, in the best case, a couple of second, so it would be non-viable in the long run if we need millions of retries\
    

## RLHelper
Helper for the IH3A. This helper is composed of 2 apps:\
    **Management API:** An API to help reset the database. This will clean the database and update the data, so the ML is not able to cheat the mechanism trying a user-name password tuple he already know. This should be called after every successful attack. Also, it will restart the WebApps services if needed\
\
   **SyslogServer:** A tailor-made syslog service that response to 2 specific requirements:\
   \
    1. Use shared memory to send messages to IH3A to avoid delays in service consumption or reading files\
    2. Specific parser for this test case. It parses Suricata, OSSEC and ModSecurity logs\
\
    **Challenges:**\
    \
    1. Work as fast as possible to avoid delays\
    2. When updating the database, use passwords as "real" as they can be. The idea is to learn based on user types (e.g: admin -> strong or default passwords, languaje of passwords based on username, etc.)\
    3. We need a huge repository of different passwords to avoid reuse. If IH3A know the password in advance, he'll score high even if it's *busted*\
    

## WebApps
\
    2 different web applications done for testing bruteforce attacks\
    **WebApp1:** WebApp using basic Form login with cookies. This app won't have any aditional protection\
    **WebApp2:** WebApp using REST API and JWT for login. This app will block a user for a couple of seconds after 5 failed attampt\
\
    **Challenges:**\
    1. Build a complete playground for IH3A. As complete as possible so he can learn different *real-life* configurations\
    2. Build a playground for different types of attacks. In this case, we are trying just brute force attacks, but more could be done\
