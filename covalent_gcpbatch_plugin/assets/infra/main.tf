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

resource "random_string" "default_prefix" {
  length  = 9
  upper   = false
  special = false
}

data "google_client_config" "current" {}


locals {
  region     = coalesce(data.google_client_config.current.region, var.region)
  project_id = coalesce(data.google_client_config.current.project, var.project_id)

  prefix   = var.prefix != "" ? var.prefix : random_string.default_prefix.result
  key_path = var.key_path != "" ? var.key_path : "${pathexpand("~")}/.config/gcloud/application_default_credentials.json"

  executor_image_tag = join("/", [join("-", [local.region, "docker.pkg.dev"]), var.project_id, "covalent", "covalent-gcpbatch-executor"])

  executor_config_content = templatefile("${path.module}/gcpbatch.conf.tftpl", {
    project_id               = var.project_id
    covalent_package_version = var.covalent_package_version
    key_path                 = var.key_path
  })
}

provider "google" {
  project     = var.project_id
  region      = "us-east1"
  credentials = local.key_path
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
  registry_auth {
    address     = "https://${local.region}-docker.pkg.dev"
    config_file = pathexpand("~/.docker/config.json")
  }
}

# Create the docker artifact registry
resource "google_artifact_registry_repository" "covalent" {
  location      = local.region
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
  name          = join("-", ["covalent", local.prefix, "storage", "bucket"])
  location      = local.region
  force_destroy = true
}

# Create custom service account for running the batch job
resource "google_service_account" "covalent" {
  account_id   = join("-", ["covalent", local.prefix, "saaccount"])
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

resource "local_file" "executor_config" {
  content  = local.executor_config_content
  filename = "${path.module}/gcpbatch.conf"
}

