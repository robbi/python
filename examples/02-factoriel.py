def factoriel(nombre):
    resultat = 1
    for i in range(nombre):
        resultat *= i
    return resultat


factoriel(10)
