terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
      version = "3.0.1"
    }
  }
}

provider google {
  project = var.project_id
  region  = "us-east1"
}

provider docker {
  host = "unix:///var/run/docker.sock"
}

data google_client_config current {}

locals {
  executor_image_tag = join("/", [join("-", [data.google_client_config.current.region, "docker.pkg.dev"]), var.project_id, "covalent", "covalent-gcpbatch-executor"])
}

resource random_string sasuffix {
  length = 16
  lower = false
  special = false
}

# Create the docker artifact registry
resource google_artifact_registry_repository covalent {
  location      = data.google_client_config.current.region
  repository_id = "covalent"
  description   = "Covalent Batch executor base images"
  format        = "DOCKER"
}

resource null_resource docker_access_token {
  provisioner local-exec {
    command = "export TF_VAR_access_token=$(gcloud auth print-access-token)"
  }
}

resource docker_image base_executor {
  depends_on = [null_resource.docker_access_token]
  name = local.executor_image_tag
  build {
    context = var.context
    build_args = {
      "PRE_RELEASE": var.prerelease
      "COVALENT_PACKAGE_VERSION": var.covalent_package_version

    }
    label = {
      author = "Agnostiq Inc"
    }

    auth_config {
      host_name = "https://${data.google_client_config.current.region}-docker.pkg.dev"
      user_name = "oauth2accesstoken"
      password = var.access_token
    }
  }
}

resource docker_registry_image base_executor {
  name = docker_image.base_executor.name
  keep_remotely = true
}

#resource null_resource build_image {
#  depends_on = [null_resource.docker_login]
#  provisioner local-exec {
#    command = "docker build -t ${local.executor_image_tag} \
#              --build-arg "PRE_RELEASE=${var.pre_release}" \
#              --build-arg "COVALENT_PACKAGE_VERSION=${var.covalent_package_version}" \
#              ${var.build_context}"
#  }
#}

#resource null_resource upload_image {
#  depends_on = [null_resource.build_image]
#
#  provisioner local-exec {
#    command = "docker push ${local.executor_image_tag}"
#  }
#}

# Create a storage bucket
resource google_storage_bucket covalent {
  name            = join("-", [var.prefix, "covalent", "storage", "bucket"])
  location        = data.google_client_config.current.region
  force_destroy   = true
}

# Create custom service account for running the batch job
resource google_service_account covalent {
  account_id      = join("", [var.prefix, "covalent", "saaccount"])
  display_name    = "CovalentBatchExecutorServiceAccount"
}

resource google_project_iam_member agent_reporter {
  project = var.project_id
  role = "roles/batch.agentReporter"
  member = google_service_account.covalent.member
}

resource google_project_iam_member log_writer {
  project = var.project_id
  role = "roles/logging.logWriter"
  member = google_service_account.covalent.member
}

resource google_project_iam_member log_viewer {
  project = var.project_id
  role = "roles/logging.viewer"
  member = google_service_account.covalent.member
}

resource google_project_iam_member registry_reader {
  project = var.project_id
  role = "roles/artifactregistry.reader"
  member = google_service_account.covalent.member
}

resource google_project_iam_member storage_object_creator {
  project = var.project_id
  role = "roles/storage.objectCreator"
  member = google_service_account.covalent.member
}

resource google_project_iam_member storage_object_reader {
  project = var.project_id
  role = "roles/storage.objectViewer"
  member = google_service_account.covalent.member
}

# Create batch job configuration json
resource local_file job_config_json {
  depends_on = [
    google_storage_bucket.covalent,
    google_service_account.covalent,
  ]
  content = templatefile("${path.module}/batch_job.json", {
    container_image_uri=local.executor_image_tag,
    service_account_email=google_service_account.covalent.email,
    bucket_path="${google_storage_bucket.covalent.name}"})
  filename = "${path.module}/job.json"
}
