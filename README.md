Polly vocal notes generator ![version][version-badge]
===========================

[version-badge]: https://img.shields.io/badge/version-0.0.1-blue.svg

With this project (take from ACloudGuru course) you can generate a simple ServerLess application that saves the text as audio file by leveraging on AWS Polly service.
The app uses the following AWS services:

- AWS Lambda functions: there are three Lambda functions:

    1. /posts [POST]: it adds the text to a DynamoDB table and publish a message to a SNS topic
    2. /posts/post_id [GET]: return the info of the given message
    3. convert_to_audio() is a pure lambda function, which is responsible to get the text, to convert it in an audio file by using the Polly API and save the file in S3
- AWS SNS: it's used to trigger the text to audio conversion
- AWS DynamoDB: here we stored the message in plain text.
- AWS S3: here we store the audio file and it's used to host the front-end app

The Lambda functions are deployed by using the [Chalice]() framework.

[Chalice]: http://chalice.readthedocs.io/en/latest/

Quickstart
==========

Provision all the needed AWS services (SNS Topic, DynamoDB table the S3 buckets and the IAM Role for the Lambda function) by running the ClouFormation template **polly.yml**. Be sure to provide the following parameters:

1. **AudioBucketName**: the name of the bucket where storing the audio file
2. **WebsiteBucketName**: the name of the bucket where hosting the website
3. **TableName**: The DynamoDb table where storing the text messages.

The CF template will return the following parameters:

1. **PollyTopicArn**: the ARN of the SNS topic
2. **WebsiteURL**: The website URL of the bucket where host the front-end
3. **RoleTopicArn**: The ARN of the Lambda role

Install the `chalice` command line utility and make this changes to the **config.json** file in the .chalice directory

- **iam_role_arn** paste here the value returned by the CF script in the RoleTopicArn variable
- **DB_TABLE_NAME** paste here the DynamoDB table name
- **SNS_TOPIC** paste here the value returned by the CF script in the PollyTopicArn variable
- **BUCKET_NAME** paste here the AudioBucketName

Deploy the lambda functions by running the `chalice deploy` command in the project directory. It will return the _API gateway URL_.

Copy the API gateway URL and copy in the **API_ENDPOINT** variable that you find in the website/scripts.js file ( **N.B.** keep the /posts as final part of the URL)

Copy all the content of the website folder in the **WebsiteBucketName** bucket.

Navigate to the **WebsiteURL** url and enjoy the app.


