# TODO - Améliorations futures

## Priorité haute
- [ ] Ajouter support pour d'autres pharmacies (Pharmashopi, 1001pharmacies)
- [ ] Améliorer la gestion des timeouts pour Pharma-GDD
- [ ] Ajouter export CSV en plus du JSON
- [ ] Implémenter un cache des résultats de recherche

## Priorité moyenne
- [ ] Ajouter un mode verbose pour le debugging
- [ ] Créer une interface web simple (Flask)
- [ ] Ajouter des statistiques de scraping (temps, succès/échecs)
- [ ] Implémenter un système de queue pour gros volumes

## Priorité basse
- [ ] Ajouter support d'autres formats d'export (XML, Excel)
- [ ] Créer un dashboard de monitoring
- [ ] Ajouter des notifications (email, webhook)
- [ ] Support multi-langue

## Bugs connus
- Pharma-GDD peut bloquer après plusieurs requêtes rapides
  → Workaround: retry avec rotation Tor implémenté
- Drakkars retourne parfois plusieurs résultats pour un EAN
  → Vérifie qu'il y a qu'un seul résultat
