index = 0


def increment():
    global index
    index += 1
    return index


print("increment =", increment())
print("increment =", increment())
print("increment =", increment())
