output service_account_email {
  value = google_service_account.covalent.email
}

output service_account_member {
  value = google_service_account.covalent.member
}

output artifact_registry_name {
  value = google_artifact_registry_repository.covalent.name
}

output artifact_registry_id {
  value = google_artifact_registry_repository.covalent.id
}
