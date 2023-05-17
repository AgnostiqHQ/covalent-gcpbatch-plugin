# Copyright 2023 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the GNU Affero General Public License 3.0 (the "License").
# A copy of the License may be obtained with this software package or at
#
#      https://www.gnu.org/licenses/agpl-3.0.en.html
#
# Use of this file is prohibited except in compliance with the License. Any
# modifications or derivative works of this file must retain this copyright
# notice, and modified files must contain a notice indicating that they have
# been altered from the originals.
#
# Covalent is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the License for more details.
#
# Relief from the License may be granted by purchasing a commercial license.

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
