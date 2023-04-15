# Quelle est l'erreur ?

def factoriel(nombre):
    resultat = 1
    for i in range(nombre):
        resultat *= i
    return resultat


def factoriel_rec(nombre):
    if nombre <= 1:
        return 1
    return nombre * factoriel_rec(nombre - 1)


print("factoriel(10) = " + str(factoriel(10)))
print("factoriel_rec(10) = " + str(factoriel_rec(10)))
