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
