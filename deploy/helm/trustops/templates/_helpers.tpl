{{/*
Expand the name of the chart.
*/}}
{{- define "trustops.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Fully qualified app name (release-name-chart-name, truncated to DNS limits).
*/}}
{{- define "trustops.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Chart label (chart-name-version).
*/}}
{{- define "trustops.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Standard label set applied to every resource.
*/}}
{{- define "trustops.labels" -}}
helm.sh/chart: {{ include "trustops.chart" . }}
{{ include "trustops.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "trustops.selectorLabels" -}}
app.kubernetes.io/name: {{ include "trustops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Resolve the service account name.
*/}}
{{- define "trustops.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "trustops.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Image reference (repository:tag, defaulting tag to appVersion).
*/}}
{{- define "trustops.image" -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s:%s" .Values.image.repository $tag -}}
{{- end -}}

{{/*
Return "true" when Helm values configure an authentication path (OIDC, SAML,
API-only insecure override with acknowledgement, or explicit auth secret).
*/}}
{{- define "trustops.authConfigured" -}}
{{- if and .Values.security.allowInsecureNoAuth (eq .Values.security.allowInsecureOverride "acknowledged") -}}
true
{{- else -}}
{{- $found := false -}}
{{- range .Values.env -}}
{{- if or (eq .name "TRUSTOPS_OIDC_CLIENT_ID") (eq .name "TRUSTOPS_SAML_IDP_METADATA_URL") (eq .name "TRUSTOPS_SESSION_SECRET") (eq .name "TRUSTOPS_COOKIE_SIGNING_KEY") -}}
{{- $found = true -}}
{{- end -}}
{{- end -}}
{{- if $found -}}true{{- else -}}false{{- end -}}
{{- end -}}
{{- end -}}
