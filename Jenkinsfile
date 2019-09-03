pipeline {
    agent any
    environment {
        APP_IMAGE = "${APP_REGISTRY}/${env.JOB_NAME}:${env.GIT_COMMIT}"
        DOC_TARGET = "${WWW_ROOT_DIR}/${env.JOB_NAME}/doc"
        LOG_NAME = "${env.JOB_NAME}"
    }
    stages {
        stage('Build') {
            steps {
                sh "docker build -t ${APP_IMAGE} ."
                sh "docker push ${APP_IMAGE}"
            }
        }
        stage('Deploy') {
            steps {
                sh "docker stack deploy --prune -c docker-stack.yml ${env.JOB_NAME}"
                sh "mkdir -p ${DOC_TARGET} && rm -r ${DOC_TARGET} && cp -r doc/ ${DOC_TARGET}"
            }
        }
    }
    post {
        always {
            mail to: "${DEVELOPER_EMAIL}",
                 subject: "[${currentBuild.currentResult}] CI: ${currentBuild.fullDisplayName}",
                 body: """Project: ${env.JOB_NAME}<br>
                          Build Number: ${env.BUILD_NUMBER}<br>
                          Build Result: ${currentBuild.currentResult}<br>
                          Duration: ${currentBuild.durationString}<br>
                          Git Commit: ${env.GIT_COMMIT}<br><br>
                          Check console output at ${env.BUILD_URL} to view the results.""",
                 mimeType: "text/html"
        }
    }
}
