from chalice import Chalice
import boto3
import os
import uuid
import json
from contextlib import closing
from boto3.dynamodb.conditions import Key, Attr
import json

app = Chalice(app_name='pollyapp')

@app.route('/posts', methods=['POST'], cors=True)
def add():
    request = app.current_request
    body = request.json_body
    record_id = str(uuid.uuid4())
    voice = body['voice']
    text = body['text']

    print("Gnerating new DynamoDB record, with ID: " + record_id)
    print("Input Text " + text)
    print("Selected Voice " + voice)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DB_TABLE_NAME'])
    table.put_item(
        Item={
            'id':record_id,
            'text':text,
            'voice':voice,
            'status':'PROCESSING'
        }
    )
    client = boto3.client('sns')
    client.publish(
        TopicArn=os.environ['SNS_TOPIC'],
        Message=record_id
    )

    return {"record_id":record_id}

@app.route("/posts/{post_id}", cors=True)
def get_posts(post_id):

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DB_TABLE_NAME'])

    if post_id == "*":
        items = table.scan()
    else:
        items = table.query(
            KeyConditionExpression=Key('id').eq(post_id)
        )
    return json.dumps(items['Items'])



@app.lambda_function()
def convert_to_audio(event, context):
    post_id = event["Records"][0]["Sns"]["Message"]

    print("Post ID " + post_id)

    #Retriving information about the post from DynamoDB table
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ['DB_TABLE_NAME'])
    post_item = table.query(
        KeyConditionExpression=Key("id").eq(post_id)
    )
    text = post_item['Items'][0]['text']
    voice = post_item['Items'][0]['voice']

    print("Retrieved text " + text)
    print("Retrieved voice " + voice)

    """
    Because single invocation of the polly synthetize_speech api can
    transform text with about 1500 characters, we are dividing the post
    into blocks of approximately 1000 characters.
    """
    rest = text
    text_blocks = []
    while len(rest) > 1100:
        begin = 0
        end = rest.find(".", 1000)
        if end == -1:
            end = rest.find(" ", 1000)

        text_block = rest[begin:end]
        rest = rest[end:]
        text_blocks.append(text_block)
    text_blocks.append(rest)

    # For each block invoke Polly API, which will transform text info audio
    polly = boto3.client('polly')
    for text_block in text_blocks:
        response = polly.synthesize_speech(
            OutputFormat='mp3',
            Text=text_block,
            VoiceId=voice
        )

        """
        Save the AudioStream returned by Amazon Polly on Lambda's temp
        directory. If there are multiple text blocks, the audio stream
        will be combined into a single file
        """
        if "AudioStream" in response:
            with closing(response["AudioStream"]) as stream:
                output = os.path.join("/tmp/", post_id)
                with open(output, "ab") as file:
                    file.write(stream.read())

    s3 = boto3.client('s3')
    s3.upload_file('/tmp/'+post_id,
                   os.environ['BUCKET_NAME'],
                   post_id + ".mp3")
    s3.put_object_acl(ACL="public-read",
                      Bucket=os.environ['BUCKET_NAME'],
                      Key=post_id+".mp3")

    location = s3.get_bucket_location(Bucket=os.environ['BUCKET_NAME'])
    region = location['LocationConstraint']

    if region is None:
        url_begin = "https://s3.amazonaws.com/"
    else:
        url_begin = "https://s3-"+str(region)+".amazonaws.com/"

    url = url_begin + str(os.environ['BUCKET_NAME'])+"/"+str(post_id)+".mp3"

    # updating the item in DynamoDb
    response = table.update_item(
        Key={'id':post_id},
        UpdateExpression="SET #statusAtt = :status_value, #urlAtt = :url_value",
        ExpressionAttributeValues={':status_value':'UPDATED', ':url_value':url},
        ExpressionAttributeNames={'#statusAtt':'status', '#urlAtt': 'url'}
    )
    return {}
