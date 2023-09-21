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
