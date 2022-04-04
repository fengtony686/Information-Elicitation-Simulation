from cmath import nan
from hashlib import new
import numpy as np
import matplotlib.pyplot as plt


class informationElicitationGame:
    def __init__(self, probabilityDict, mechanism):
        self.mechanism = mechanism
        self.probabilityDict = probabilityDict
        self.agentNum = len(list(self.probabilityDict.keys())[0])
        self.optionNum = int(len(probabilityDict) / self.agentNum)
        self.strategyNum = np.power(self.optionNum, self.optionNum)
        self.reports = np.array([[] for _ in range(self.agentNum)])
        self.options = np.array([[] for _ in range(self.agentNum)])
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

    # Here are the mechanism functions.
    def dynamicSelfAgreement(self, currentReport, currentAgentIndex):
        payoff = -1
        if (self.reports.shape[1] == 0):
            return 0
        for i in currentReport:
            if i == currentReport[currentAgentIndex]:
                payoff += 1
        payoff /= len(currentReport) - 1
        payoff -= (self.reports[currentAgentIndex][-1] ==
                   currentReport[currentAgentIndex]) / (self.reports.shape[1] + 1)
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

    def addReports(self, currentReport, currentOptions):
        self.reports = np.hstack((self.reports, np.array([currentReport]).T))
        # print(self.reports, currentReport)
        self.options = np.hstack((self.options, np.array([currentOptions]).T))
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
        # print(currentReports, currentOptions, signals)
        for i in range(self.agentNum):
            allStrategyPayoff = []
            for strategy in range(self.strategyNum):
                counterfactualReports = currentReports.copy()
                counterfactualReports[i] = self.optionToReport(
                    strategy, signals[i])
                if self.mechanism == "Self Agreement":
                    allStrategyPayoff.append(
                        self.selfAgreement(counterfactualReports, i))
                elif self.mechanism == "Dynamic Self Agreement":
                    allStrategyPayoff.append(
                        self.dynamicSelfAgreement(counterfactualReports, i))
            self.agents[i].possiblePayoffs = np.hstack(
                (self.agents[i].possiblePayoffs, np.array([allStrategyPayoff]).T))
        self.addReports(currentReports, currentOptions)
        # print(currentReports)


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
        if self.strategy == "FLP":
            accumulateRewards = np.array([])
            for i in range(self.strategyNum):
                accumulateRewards = np.append(accumulateRewards, np.sum(
                    self.possiblePayoffs[i]) + np.random.rand() * 10)
            return np.argmax(accumulateRewards)
        elif self.strategy == "Replicator Dynamics":
            if len(self.reports) == 0:
                for i in range(self.strategyNum):
                    self.strategyProbList.append(1/self.strategyNum)
            else:
                accumulateRewards = np.array([])
                for i in range(self.strategyNum):
                    accumulateRewards = np.append(accumulateRewards, np.sum(
                        self.possiblePayoffs[i]) + np.random.rand() * 10)
                averageRewards = accumulateRewards / len(self.reports)
                totalAverage = np.sum(
                    [self.strategyProbList[i] * averageRewards[i] for i in range(self.strategyNum)])
                newStrategyProbList = []
                for i in range(self.strategyNum):
                    newStrategyProbList.append(
                        self.strategyProbList[i] * averageRewards[i] / totalAverage)
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
                    upperConfidenceBound = np.append(upperConfidenceBound, np.sqrt(np.log(len(
                        self.reports)) / self.options.count(i)) if self.options.count(i) != 0 else np.sqrt(np.log(len(self.reports)) * 2))
                else:
                    upperConfidenceBound = np.append(
                        upperConfidenceBound, np.random.rand())
            for index, i in enumerate(self.options):
                for j in range(self.strategyNum):
                    if i == j:
                        upperConfidenceBound[i] += self.possiblePayoffs[i][index] / \
                            self.options.count(i)
            return np.argmax(upperConfidenceBound)


# newGame = informationElicitationGame({(0, 0): 0.21, (0, 1): 0.01, (1, 0): 0.2, (1, 1): 0.58}, "Dynamic Self Agreement")
newGame = informationElicitationGame(
    {(0, 0): 0.03, (0, 1): 0.01, (1, 0): 0.01, (1, 1): 0.95}, "Self Agreement")
newGame.setAgents("UCB")
# newGame.setAgents("Replicator Dynamics")
for i in range(1200):
    newGame.run()

print(np.sum(newGame.agents[1].possiblePayoffs[0]), np.sum(newGame.agents[1].possiblePayoffs[1]), np.sum(
    newGame.agents[1].possiblePayoffs[2]), np.sum(newGame.agents[1].possiblePayoffs[3]))
print(np.sum(newGame.agents[0].possiblePayoffs[0]), np.sum(newGame.agents[0].possiblePayoffs[1]), np.sum(
    newGame.agents[0].possiblePayoffs[2]), np.sum(newGame.agents[0].possiblePayoffs[3]))

plt.rcParams['figure.figsize'] = (25.0, 6.0)
plt.plot(np.arange(1200), newGame.options[0], 's-', color='r', label="Agent X")
plt.plot(np.arange(1200), newGame.options[1], 'o-', color='g', label="Agent Y")
plt.xlabel("Round")
plt.ylabel("Strategy")
plt.legend(loc="best")
plt.show()
