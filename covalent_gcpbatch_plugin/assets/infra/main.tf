# Copyright 2023 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the Apache License 2.0 (the "License"). A copy of the
# License may be obtained with this software package or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Use of this file is prohibited except in compliance with the License.
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.0.1"
    }
  }
}

provider "google" {
  project     = var.project_id
  region      = "us-east1"
  credentials = file(var.key_path)
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
  registry_auth {
    address  = "https://${data.google_client_config.current.region}-docker.pkg.dev"
    username = "oauth2accesstoken"
    password = var.access_token
  }
}

data "google_client_config" "current" {}

locals {
  executor_image_tag = join("/", [join("-", [data.google_client_config.current.region, "docker.pkg.dev"]), var.project_id, "covalent", "covalent-gcpbatch-executor"])
}

resource "random_string" "sasuffix" {
  length  = 16
  lower   = false
  special = false
}

# Create the docker artifact registry
resource "google_artifact_registry_repository" "covalent" {
  location      = data.google_client_config.current.region
  repository_id = "covalent"
  description   = "Covalent Batch executor base images"
  format        = "DOCKER"
}


resource "docker_image" "base_executor" {
  name = local.executor_image_tag
  build {
    context = var.context
    build_args = {
      "PRE_RELEASE" : var.prerelease
      "COVALENT_PACKAGE_VERSION" : var.covalent_package_version
    }
    label = {
      author = "Agnostiq Inc"
    }
    platform = "linux/amd64"
  }
}

resource "docker_registry_image" "base_executor" {
  name          = docker_image.base_executor.name
  keep_remotely = true
}

# Create a storage bucket
resource "google_storage_bucket" "covalent" {
  name          = join("-", [var.prefix, "covalent", "storage", "bucket"])
  location      = data.google_client_config.current.region
  force_destroy = true
}

# Create custom service account for running the batch job
resource "google_service_account" "covalent" {
  account_id   = join("", [var.prefix, "covalent", "saaccount"])
  display_name = "CovalentBatchExecutorServiceAccount"
}

resource "google_project_iam_member" "agent_reporter" {
  project = var.project_id
  role    = "roles/batch.agentReporter"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "log_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "storage_object_creator" {
  project = var.project_id
  role    = "roles/storage.objectCreator"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "storage_object_reader" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = google_service_account.covalent.member
}

data "template_file" "executor_config" {
  template = file("${path.module}/gcpbatch.conf.tftpl")

  vars = {
    project_id               = var.project_id
    covalent_package_version = var.covalent_package_version
    key_path                 = var.key_path
  }
}

resource "local_file" "executor_config" {
  content  = data.template_file.executor_config.rendered
  filename = "${path.module}/gcpbatch.conf"
}
