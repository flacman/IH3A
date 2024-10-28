# IH3A

In this project, we present an innovative framework designed to train and build intelligent agents capable of evading network detection. Our approach focuses on dynamic parameter adjustments, success optimization, and stealthy evasion. By harnessing adaptive learning techniques, we aim to revolutionize the field of network security.

To train these agents, we propose a framework where various types of attacks can be performed, and immediate responses can be received from different defensive technologies. The proposed training schema consists of three main layers:\

**1. The Client:** This layer handles the execution of attacks. It includes the agent itself and tools to manage the environment and provide feedback to reinforce the agent's learning. The agent may use standard reinforcement learning models, agentic AI frameworks, or other compound or RAG LLM implementations. For this project, we will develop a reinforcement learning (RL) agent using policy-optimization models.

**2. The Defensive Layer:** This layer encompasses most defensive mechanisms. The framework will allow notifications from defensive mechanisms via SysLog or API consumption. All tools should be configured to send messages to the Agent Helper properly. This information is used by the Agent Helper to provide feedback to the agent. For this project, we will use OSSEC, Suricata, and ModSecurity.

**3. The Testing Layer:** This layer hosts a potential victim network, used to simulate attacks by the agent.


![Alt text](NetDiagram.png?raw=true "Title")

Our implementation for testing is composed by 3 sections:

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
