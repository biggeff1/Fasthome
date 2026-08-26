"""Libellés français centralisés pour l'interface Django Admin.

Les noms de classes et les identifiants de modèles restent inchangés pour ne
pas toucher aux migrations. Seuls les libellés affichés dans l'administration
sont personnalisés au démarrage.
"""

from django.contrib import admin


MODEL_LABELS = {
    # Utilisateurs / identité
    'User': ('Utilisateur', 'Utilisateurs'),
    'IdentityVerification': ('Vérification d’identité', 'Vérifications d’identité'),
    'IdentityVerificationAnalysis': ('Analyse de vérification', 'Analyses de vérification'),
    'IdentityVerificationEvent': ('Historique de vérification', 'Historique des vérifications'),
    # Logements
    'Property': ('Logement', 'Logements'),
    'PropertyType': ('Type de logement', 'Types de logements'),
    'PropertyPublication': ('Publication de logement', 'Publications de logements'),
    'PropertyDeclaration': ('Déclaration de logement', 'Déclarations de logements'),
    'PropertyPhoto': ('Photo de logement', 'Photos de logements'),
    'PropertyFeature': ('Caractéristique du logement', 'Caractéristiques des logements'),
    'Bedroom': ('Chambre', 'Chambres'),
    'LivingRoom': ('Salon', 'Salons'),
    'Kitchen': ('Cuisine', 'Cuisines'),
    'Bathroom': ('Salle de bain', 'Salles de bain'),
    'Toilet': ('Toilettes', 'Toilettes'),
    'CollaborationConsent': ('Consentement de collaboration', 'Consentements de collaboration'),
    'Favorite': ('Favori', 'Favoris'),
    # Visites
    'Visit': ('Visite', 'Visites'),
    'VisitRequest': ('Demande de visite', 'Demandes de visite'),
    # Location / contrats
    'Lease': ('Location', 'Locations'),
    'LeaseExit': ('Sortie de location', 'Sorties de location'),
    'RenewalRequest': ('Demande de renouvellement', 'Demandes de renouvellement'),
    'Contract': ('Contrat', 'Contrats'),
    'Incident': ('Incident', 'Incidents'),
    # Finances
    'Payment': ('Paiement', 'Paiements'),
    'PaymentRecord': ('Enregistrement de paiement', 'Enregistrements de paiement'),
    'Receipt': ('Reçu', 'Reçus'),
    # Notifications / contrôle
    'Notification': ('Notification', 'Notifications'),
    'InspectionReport': ('Rapport d’inspection', 'Rapports d’inspection'),
    'AuditLog': ('Journal d’audit', 'Journal d’audit'),
    'LogEntry': ('Entrée du journal', 'Entrées du journal'),
    # Correspondances
    'MatchingProfile': ('Profil de recherche', 'Profils de recherche'),
    'Match': ('Correspondance', 'Correspondances'),
}


def apply_french_admin_labels():
    """Applique les libellés français aux ModelAdmin déjà enregistrés."""
    for model, model_admin in admin.site._registry.items():
        labels = MODEL_LABELS.get(model.__name__)
        if not labels:
            continue
        singular, plural = labels
        model_admin.verbose_name = singular
        model_admin.verbose_name_plural = plural

    # Les modèles Django natifs restent automatiquement traduits par Django
    # grâce à LANGUAGE_CODE=fr-fr.
