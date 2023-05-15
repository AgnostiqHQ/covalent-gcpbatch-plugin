output service_account_email {
  value = google_service_account.covalent.email
}

output container_image_uri {
  value = local.executor_image_tag
}

output storage_bucket_name {
  value = google_storage_bucket.covalent.name
}

output GCPBatchExecutor {
  value = <<EOL
  GCPBatchExecutor(
    project_id='${data.google_client_config.current.project}',
    region='${data.google_client_config.current.region}',
    bucket_name='${google_storage_bucket.covalent.name}',
    container_image_uri='${local.executor_image_tag}',
    service_account_email='${google_service_account.covalent.email}'
  )
EOL
}
