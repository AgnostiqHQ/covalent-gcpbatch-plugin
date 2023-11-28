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
  # Try to get region from current config, otherwise use vars.
  region     = coalesce(data.google_client_config.current.region, var.region)
  project_id = coalesce(data.google_client_config.current.project, var.project_id)

  # Use random prefix if var not set.
  prefix = var.prefix != "" ? var.prefix : random_string.default_prefix.result

  # Repository and iamge configuration.
  repository_base_url = join("-", [local.region, "docker.pkg.dev"])
  repository_id       = "covalent-executor-${local.prefix}"

  executor_image_name = join("/", [
    local.repository_base_url,
    local.project_id,
    local.repository_id,
    "covalent-gcpbatch-executor"
  ])
  executor_config_content = templatefile("${path.root}/gcpbatch.conf.tftpl", {
    covalent_package_version = var.covalent_package_version
    project_id               = local.project_id
    key_path                 = local.key_path
  })

  # Use default key path if var not set.
  key_path_default = "${pathexpand("~")}/.config/gcloud/application_default_credentials.json"
  key_path         = var.key_path != "" ? var.key_path : local.key_path_default

  # Distinguish normal versus editable (-e) plugin installs.
  editable_install = !fileexists("./Dockerfile")

  # Image build context and file locations.
  build_context = local.editable_install ? "../../.." : path.module
  build_files   = local.build_context

  # Build arguments for docker image.
  exec_script_location = local.editable_install ? "covalent_gcpbatch_plugin/exec.py" : "exec.py"
  build_args = {
    covalent_package_version = var.covalent_package_version
    prerelease               = var.prerelease
    exec_script_arg          = "${local.build_files}/${local.exec_script_location}"
    requirements_file_arg    = "${local.build_files}/requirements.txt"
  }
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

resource "google_artifact_registry_repository" "covalent" {
  location      = local.region
  repository_id = local.repository_id
  description   = "Covalent Batch executor base images"
  format        = "DOCKER"
}


resource "docker_image" "base_executor" {
  name = local.executor_image_name

  build {
    context  = local.build_context
    platform = "linux/amd64"

    build_args = {
      "COVALENT_PACKAGE_VERSION" : local.build_args.covalent_package_version
      "PRE_RELEASE" : local.build_args.prerelease
      "EXEC_SCRIPT" : local.build_args.exec_script_arg
      "REQUIREMENTS_FILE" : local.build_args.requirements_file_arg
    }
    label = {
      author = "Agnostiq Inc"
    }
  }
}

resource "docker_registry_image" "base_executor" {
  name          = docker_image.base_executor.name
  keep_remotely = false
}

resource "google_storage_bucket" "covalent" {
  name          = join("-", ["covalent", "storage", local.prefix])
  location      = local.region
  force_destroy = true
}

resource "google_service_account" "covalent" {
  account_id   = join("-", ["covalent", "sa", local.prefix])
  display_name = "CovalentBatchExecutorServiceAccount"
  description  = "Service account created by Covalent deployment"
  project      = local.project_id
}

resource "google_project_iam_member" "agent_reporter" {
  project = local.project_id
  role    = "roles/batch.agentReporter"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "log_writer" {
  project = local.project_id
  role    = "roles/logging.logWriter"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "log_viewer" {
  project = local.project_id
  role    = "roles/logging.viewer"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "registry_writer" {
  project = local.project_id
  role    = "roles/artifactregistry.writer"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "storage_object_creator" {
  project = local.project_id
  role    = "roles/storage.objectCreator"
  member  = google_service_account.covalent.member
}

resource "google_project_iam_member" "storage_object_reader" {
  project = local.project_id
  role    = "roles/storage.objectViewer"
  member  = google_service_account.covalent.member
}

resource "local_file" "executor_config" {
  content  = local.executor_config_content
  filename = "${path.module}/gcpbatch.conf"
}
