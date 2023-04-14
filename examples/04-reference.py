def double(x):
    x += x
    return x


def double_dict(x: dict):
    items = list(x.items())
    for k, v in items:
        x[double(k)] = double(v)
    return x

TAILLE_TITRE = 50


print("### entier (int) ".ljust(TAILLE_TITRE, "#"))
a = 3
print(f"{a=}")
b = a
print(f">>> b = a\n{b=}")
b += 2
print(f">>> b += 2\n{a=} {b=}")
print(f">>> double(a)")
print(double(a))
print(f"{a=} {b=}")

print("### liste (list) ".ljust(TAILLE_TITRE, "#"))
a = [3]
print(f"{a=}")
b = a
print(f">>> b = a\n{b=}")
a.append(1)
print(f">>> a.append(1)\n{a=} {b=}")
b += [2]
print(f">>> b += [2]\n{a=} {b=}")
b.append(5)
print(f">>> b.append(5)\n{a=} {b=}")
b = b + [2]
print(f">>> b = b + [2]\n{a=} {b=}")
print(f">>> double(a)")
print(double(a))
print(f"{a=} {b=}")

print("### tuple ".ljust(TAILLE_TITRE, "#"))
a = (3,)
print(f"{a=}")
b = a
print(f">>> b = a\n{b=}")
b += (2,)
print(f">>> b += (2,)\n{a=} {b=}")
b = b + (2,)
print(f">>> b = b + (2,)\n{a=} {b=}")
print(f">>> double(a)")
print(double(a))
print(f"{a=} {b=}")

print("### dictionnaire (dict) ".ljust(TAILLE_TITRE, "#"))
a = {'a': 1}
print(f"{a=}")
b = a
print(f">>> b = a\n{b=}")
a['b'] = 2
b['c'] = 3
print(f">>> a['b'] = 2\n>>> b['c'] = 3")
print(f"{a=} {b=}")
print(f">>> double_dict(a)")
print(double_dict(a))
print(f"{a=} {b=}")
