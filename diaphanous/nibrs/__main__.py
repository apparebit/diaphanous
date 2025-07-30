from .util import configure
from .data import load


if __name__ == "__main__":
    configure()
    data = load()
    offenders = data.offender_demographics()

    print(data.caseload())
    print(data.severity())
    print(data.completion())
    print((lambda pair: pair[1])(offenders.age_distribution()))
