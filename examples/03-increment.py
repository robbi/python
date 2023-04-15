index = 0


def increment():
    # Que se passe-t-il si on ne déclare pas la variable globale ?
    global index
    index += 1
    return index


print("increment =", increment())
print("increment =", increment())
print("increment =", increment())
