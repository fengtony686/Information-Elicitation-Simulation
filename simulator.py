from cmath import nan
from hashlib import new
from traceback import print_tb
from tqdm import trange
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator


'''
--------------------- Class of Game ----------------------------
'''


class informationElicitationGame:
    def __init__(self, probabilityDict, mechanism):
        self.mechanism = mechanism
        self.probabilityDict = probabilityDict
        self.agentNum = len(list(self.probabilityDict.keys())[0])
        self.optionNum = int(np.power(len(probabilityDict), 1 / self.agentNum))
        self.strategyNum = np.power(self.optionNum, self.optionNum)
        self.reports = np.array([[] for _ in range(self.agentNum)])
        self.options = np.array([[] for _ in range(self.agentNum)])
        self.signals = np.array([[] for _ in range(self.agentNum)])
        self.agents = []

    def setAgents(self, strategy):
        for _ in range(self.agentNum):
            self.agents.append(
                agent(strategy=strategy, optionNum=self.optionNum))

    def optionToReport(self, option, signal):
        report = (option % np.power(self.optionNum, self.optionNum - signal)
                  ) / np.power(self.optionNum, self.optionNum - signal - 1)
        # print(option, signal, int(report))
        return int(report)

    def generateSignals(self):
        seed = np.random.rand()
        leftBound = 0
        for (signal, probability) in self.probabilityDict.items():
            rightBound = leftBound + probability
            if seed < rightBound and seed >= leftBound:
                return signal
            else:
                leftBound = rightBound
        return nan

    def addReports(self, currentReport, currentOptions, currentSignals):
        self.reports = np.hstack((self.reports, np.array([currentReport]).T))
        # print(self.reports, currentReport)
        self.options = np.hstack((self.options, np.array([currentOptions]).T))
        self.signals = np.hstack((self.signals, np.array([currentSignals]).T))
        for index, i in enumerate(currentReport):
            self.agents[index].reports.append(i)
            self.agents[index].options.append(currentOptions[index])

    # Processing one round of game.
    def run(self):
        signals = self.generateSignals()
        currentOptions = []
        for i in range(self.agentNum):
            currentOptions.append(self.agents[i].chooseOption())
        currentReports = []
        for i in range(self.agentNum):
            currentReports.append(self.optionToReport(
                currentOptions[i], signals[i]))
        for i in range(self.agentNum):
            allStrategyPayoff = []
            for strategy in range(self.strategyNum):
                if self.mechanism == "Gap DMI":
                    if self.reports.shape[1] % (2 * self.optionNum) != 2*self.optionNum - 1:
                        allStrategyPayoff.append(0)
                    else:
                        reportsMat = np.zeros(
                            (self.agentNum, 2 * self.optionNum))
                        for j in range(self.agentNum):
                            for k in range(2 * self.optionNum - 1):
                                if j != i:
                                    reportsMat[j][k] = self.reports[j][-2 *
                                                                       self.optionNum + 1 + k]
                                else:
                                    reportsMat[j][k] = self.optionToReport(
                                        strategy, self.signals[j][-2 * self.optionNum + 1 + k])
                        for j in range(self.agentNum):
                            if j != i:
                                reportsMat[j][-1] = currentReports[j]
                            else:
                                reportsMat[j][-1] = self.optionToReport(
                                    strategy, signals[j])
                        allStrategyPayoff.append(self.GapDMI(reportsMat, i))

                counterfactualReports = currentReports.copy()
                counterfactualReports[i] = self.optionToReport(
                    strategy, signals[i])
                if self.mechanism == "Self Agreement":
                    allStrategyPayoff.append(
                        self.selfAgreement(counterfactualReports, i))
                elif self.mechanism == "Dynamic Self Agreement":
                    allStrategyPayoff.append(
                        self.dynamicSelfAgreement(counterfactualReports, i))
                elif self.mechanism == "Dynamic Mixed Agreement":
                    allStrategyPayoff.append(
                        self.dynamicMixedAgreement(counterfactualReports, i))
                elif self.mechanism == "Agreement":
                    allStrategyPayoff.append(
                        self.agreement(counterfactualReports, i))
                elif self.mechanism == "DMI":
                    allStrategyPayoff.append(
                        self.DMI(counterfactualReports, i))
            self.agents[i].possiblePayoffs = np.hstack(
                (self.agents[i].possiblePayoffs, np.array([allStrategyPayoff]).T))
        self.addReports(currentReports, currentOptions, signals)
        # print(currentReports)

    '''
    ------------------------ Here are the Mechanism Functions -----------------------
    '''

    def dynamicSelfAgreement(self, currentReport, currentAgentIndex):
        payoff = -1
        if (self.reports.shape[1] == 0):
            return 0
        for i in currentReport:
            if i == currentReport[currentAgentIndex]:
                payoff += 1
        payoff /= len(currentReport) - 1
        payoff -= (self.reports[currentAgentIndex][-1] ==
                   currentReport[currentAgentIndex]) / (self.reports.shape[1] + 1) * 2
        payoff += 1
        return payoff

    def dynamicMixedAgreement(self, currentReport, currentAgentIndex):
        payoff = -1
        if (self.reports.shape[1] == 0):
            return 0
        for i in currentReport:
            if i == currentReport[currentAgentIndex]:
                payoff += 1
        payoff /= len(currentReport) - 1
        payoff -= (self.reports[currentAgentIndex][-1] ==
                   currentReport[currentAgentIndex]) / (self.reports.shape[1] + 1)
        agreementTerm = 0
        for i in range(self.agentNum):
            if i != currentAgentIndex and self.reports[i][-1] == currentReport[currentAgentIndex]:
                agreementTerm += 1
        payoff -= (agreementTerm / (self.agentNum - 1))
        payoff += 1
        return payoff

    def agreement(self, currentReport, currentAgentIndex):
        payoff = -1
        if (self.reports.shape[1] == 0):
            return 0
        for i in currentReport:
            if i == currentReport[currentAgentIndex]:
                payoff += 1
        payoff /= len(currentReport) - 1
        agreementTerm = 0
        for i in range(self.agentNum):
            if i != currentAgentIndex and self.reports[i][-1] == currentReport[currentAgentIndex]:
                agreementTerm += 1
        payoff -= (agreementTerm / (self.agentNum - 1))
        payoff += 1
        return payoff

    def DMI(self, currentReport, currentAgentIndex):
        if (self.reports.shape[1] < 2 * self.optionNum - 1):
            return 0
        payoff = 0
        for i in range(self.agentNum):
            if i != currentAgentIndex:
                frequencyMatrix1 = np.zeros((self.optionNum, self.optionNum))
                frequencyMatrix2 = np.zeros((self.optionNum, self.optionNum))
                for j in range(self.optionNum):
                    frequencyMatrix1[int(self.reports[i][-self.optionNum-j])][int(
                        self.reports[currentAgentIndex][-self.optionNum-j])] += 1
                for j in range(self.optionNum - 1):
                    frequencyMatrix2[int(self.reports[i][-1-j])
                                     ][int(self.reports[currentAgentIndex][-1-j])] += 1
                frequencyMatrix2[int(currentReport[i])
                                 ][int(currentReport[currentAgentIndex])] += 1
                payoff += np.linalg.det(frequencyMatrix1) * \
                    np.linalg.det(frequencyMatrix2)
        return payoff

    def selfAgreement(self, currentReport, currentAgentIndex):
        if (self.reports.shape[1] == 0):
            return 0
        payoff = -1
        for i in currentReport:
            if i == currentReport[currentAgentIndex]:
                payoff += 1
        payoff /= len(currentReport) - 1
        payoff -= int(self.reports[currentAgentIndex]
                      [-1]) == currentReport[currentAgentIndex]
        payoff += 1
        # if currentAgentIndex == 1:
        #     print(currentReport, self.reports[currentAgentIndex][-1])
        return payoff

    def GapDMI(self, currentReport, currentAgentIndex):
        if (self.reports.shape[1] % (2 * self.optionNum) != 2 * self.optionNum - 1):
            return 0
        payoff = 0
        for i in range(self.agentNum):
            if i != currentAgentIndex:
                frequencyMatrix1 = np.zeros((self.optionNum, self.optionNum))
                frequencyMatrix2 = np.zeros((self.optionNum, self.optionNum))
                for j in range(self.optionNum):
                    frequencyMatrix1[int(currentReport[i][-self.optionNum-j-1])][int(
                        currentReport[currentAgentIndex][-self.optionNum-j-1])] += 1
                for j in range(self.optionNum):
                    frequencyMatrix2[int(currentReport[i][-1-j])
                                     ][int(currentReport[currentAgentIndex][-1-j])] += 1
                payoff += np.linalg.det(frequencyMatrix1) * \
                    np.linalg.det(frequencyMatrix2)
        # if payoff != 0:
        #     print(payoff)
        return payoff


'''
----------------------- Class of Agents --------------------------
'''


class agent:
    def __init__(self, strategy, optionNum):
        self.optionNum = optionNum
        self.strategy = strategy
        self.strategyNum = np.power(self.optionNum, self.optionNum)
        self.options = []
        self.reports = []
        self.strategyProbList = []
        self.possiblePayoffs = np.array([[] for _ in range(self.strategyNum)])

    def chooseOption(self):
        if self.strategy == "FPL10":
            accumulateRewards = np.array([])
            for i in range(self.strategyNum):
                accumulateRewards = np.append(accumulateRewards, np.sum(
                    self.possiblePayoffs[i]) + np.random.rand() * 10)
            return np.argmax(accumulateRewards)
        elif self.strategy == "FPL20":
            accumulateRewards = np.array([])
            for i in range(self.strategyNum):
                accumulateRewards = np.append(accumulateRewards, np.sum(
                    self.possiblePayoffs[i]) + np.random.rand() * 20)
            return np.argmax(accumulateRewards)
        elif self.strategy == "FPL5":
            accumulateRewards = np.array([])
            for i in range(self.strategyNum):
                accumulateRewards = np.append(accumulateRewards, np.sum(
                    self.possiblePayoffs[i]) + np.random.rand() * 5)
            return np.argmax(accumulateRewards)
        elif self.strategy == "Replicator Dynamics":
            if len(self.reports) == 0:
                for i in range(self.strategyNum):
                    self.strategyProbList.append(1 / self.strategyNum)
            else:
                beta = 1
                accumulateRewards = np.array([])
                for i in range(self.strategyNum):
                    accumulateRewards = np.append(accumulateRewards, np.sum(
                        self.possiblePayoffs[i]))
                averageRewards = accumulateRewards / len(self.reports)
                totalAverage = np.sum([self.strategyProbList[i] * (1 + np.exp(
                    beta * averageRewards[i])) for i in range(self.strategyNum)])
                newStrategyProbList = []
                for i in range(self.strategyNum):
                    newStrategyProbList.append(
                        self.strategyProbList[i] * (1 + np.exp(beta * averageRewards[i])) / totalAverage)
                self.strategyProbList = newStrategyProbList
            randomSeed = np.random.rand()
            tmpTotal = 0
            for index, i in enumerate(self.strategyProbList):
                if tmpTotal <= randomSeed and tmpTotal + i > randomSeed:
                    return index
                else:
                    tmpTotal += i
        elif self.strategy == "Memoryless Replicator Dynamics":
            if len(self.reports) == 0:
                for i in range(self.strategyNum):
                    self.strategyProbList.append(1 / self.strategyNum)
            else:
                beta = 1
                averageRewards = np.array([])
                for i in range(self.strategyNum):
                    averageRewards = np.append(averageRewards,
                                               self.possiblePayoffs[i][-1])
                # print(averageRewards)
                totalAverage = np.sum([self.strategyProbList[i] * (1 + np.exp(
                    beta * averageRewards[i])) for i in range(self.strategyNum)])
                newStrategyProbList = []
                for i in range(self.strategyNum):
                    newStrategyProbList.append(
                        self.strategyProbList[i] * (1 + np.exp(beta * averageRewards[i])) / totalAverage)
                self.strategyProbList = newStrategyProbList
            randomSeed = np.random.rand()
            tmpTotal = 0
            for index, i in enumerate(self.strategyProbList):
                if tmpTotal <= randomSeed and tmpTotal + i > randomSeed:
                    return index
                else:
                    tmpTotal += i
        elif self.strategy == "UCB":
            upperConfidenceBound = np.array([])
            for i in range(self.strategyNum):
                if len(self.reports) != 0:
                    upperConfidenceBound = np.append(
                        upperConfidenceBound,
                        np.sqrt(
                            np.log(
                                len(
                                    self.reports)) /
                            self.options.count(i)) if self.options.count(i) != 0 else np.sqrt(
                            np.log(
                                len(
                                    self.reports)) *
                            2))
                else:
                    upperConfidenceBound = np.append(
                        upperConfidenceBound, np.random.rand())
            for index, i in enumerate(self.options):
                for j in range(self.strategyNum):
                    if i == j:
                        upperConfidenceBound[i] += self.possiblePayoffs[i][index] / \
                            self.options.count(i)
            return np.argmax(upperConfidenceBound)


'''
----------------------- Converge Rate Drawing ---------------------------------
'''


def drawConvergeRate(numOfRounds, numOfRepeating, probabilityMatrix, mechanism, algorithm):
    convergeTimes = np.zeros(numOfRounds)
    for i in trange(numOfRepeating):
        newGame = informationElicitationGame(probabilityMatrix, mechanism)
        newGame.setAgents(algorithm)
        for _ in range(numOfRounds):
            newGame.run()
        index = numOfRounds - 1
        if newGame.options[0][-1] != newGame.options[1][-1]:
            continue
        converge = True
        for j in range(numOfRounds):
            if newGame.options[0][index] == newGame.options[0][-1]:
                convergeTimes[index] += converge
            else:
                converge = False
            index -= 1
        converge = True
        for j in range(numOfRounds):
            if newGame.options[1][index] == newGame.options[1][-1]:
                convergeTimes[index] += converge
            else:
                converge = False
            index -= 1
    convergeTimes = convergeTimes / (2 * numOfRepeating)
    plt.rcParams['figure.figsize'] = (25.0, 6.0)
    plt.plot(np.arange(numOfRounds), convergeTimes,
             label=mechanism+", "+algorithm)
    plt.xlabel("Round")
    plt.ylabel("Converge Proportion")
    plt.legend(loc="best")


'''
----------------------- Comparison of Converge Rate ----------------------------
'''
# drawConvergeRate(800, 200, {(0, 0): 0.3, (0, 1): 0.1, (1, 0): 0.3, (1, 1): 0.3}, "Dynamic Mixed Agreement", "FPL5")
# drawConvergeRate(800, 200, {(0, 0): 0.3, (0, 1): 0.1, (1, 0): 0.3, (1, 1): 0.3}, "Agreement", "FPL5")
# drawConvergeRate(800, 200, {(0, 0): 0.3, (0, 1): 0.1, (1, 0): 0.3, (1, 1): 0.3}, "Dynamic Mixed Agreement", "FPL10")
# drawConvergeRate(800, 200, {(0, 0): 0.3, (0, 1): 0.1, (1, 0): 0.3, (1, 1): 0.3}, "Agreement", "FPL10")
# drawConvergeRate(800, 200, {(0, 0): 0.3, (0, 1): 0.1, (1, 0): 0.3, (1, 1): 0.3}, "Agreement", "Memoryless Replicator Dynamics")
# drawConvergeRate(800, 200, {(0, 0): 0.3, (0, 1): 0.1, (1, 0): 0.3, (1, 1): 0.3}, "Dynamic Mixed Agreement", "FPL20")
# drawConvergeRate(800, 200, {(0, 0): 0.3, (0, 1): 0.1, (1, 0): 0.3, (1, 1): 0.3}, "Agreement", "FPL20")
# plt.show()


'''
------------------------- Draw the Strategies Used in One Game -------------------
'''

# newGame = informationElicitationGame(
# {(0, 0): 0.2, (1, 1): 0.2, (2, 2): 0.2, (0, 1): 0.06, (1, 0): 0.06, (0, 2): 0.07, (2, 0): 0.07, (1, 2): 0.07, (2, 1): 0.07}, "Gap DMI")
# newGame = informationElicitationGame(
#     {(0, 0): 0.06, (0, 1): 0.02, (1, 0): 0.02, (1, 1): 0.9}, "DMI")
newGame = informationElicitationGame(
{(0, 0): 0.3, (0, 1): 0.1, (1, 0): 0.3, (1, 1): 0.3}, "Gap DMI")
newGame.setAgents("FPL10")
# newGame.setAgents("UCB")
# newGame.setAgents("Memoryless Replicator Dynamics")
for i in trange(10000):
    newGame.run()

print(
    np.sum(
        newGame.agents[1].possiblePayoffs[0]), np.sum(
            newGame.agents[1].possiblePayoffs[1]), np.sum(
                newGame.agents[1].possiblePayoffs[2]), np.sum(
                    newGame.agents[1].possiblePayoffs[3]))
print(
    np.sum(
        newGame.agents[0].possiblePayoffs[0]), np.sum(
            newGame.agents[0].possiblePayoffs[1]), np.sum(
                newGame.agents[0].possiblePayoffs[2]), np.sum(
                    newGame.agents[0].possiblePayoffs[3]))
# print(newGame.agents[1].strategyProbList)

y_major_locator = MultipleLocator(1)
plt.rcParams['figure.figsize'] = (25.0, 6.0)
plt.plot(np.arange(10000), newGame.options[0], 's-', color='r', label="Agent X")
plt.plot(np.arange(10000), newGame.options[1], 'o-', color='g', label="Agent Y")
plt.xlabel("Round")
plt.ylabel("Strategy")
plt.gca().yaxis.set_major_locator(y_major_locator)
plt.legend(loc="best")
plt.show()
