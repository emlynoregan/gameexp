# add /opt to the path, to get the libraries
import sys
sys.path.append('/opt')

import json
from spelunk import get_spelunk_rec, spelunk_rec_needs_transcript, update_spelunk_rec, C_STATUS_ERROR, C_STATUS_READY, C_STATUS_UNDERWAY, spelunk_rec_needs_summary
from shared import exc_to_string
from youtube import get_youtube_transcript_url, get_youtube_summary_url
import datetime
import os
import time

def lambda_handler(event, context):
    print ("Stub Received event: " + json.dumps(event, indent=2))   

    if 'Records' in event:
        print ("Records found. This is an SQS message.")

        batchItemFailures = []

        for record in event['Records']:
            try:
                print ("Processing SQS message: " + json.dumps(record, indent=2))

                body = json.loads(record['body'])

                op = body['op'] if 'op' in body else None
                detail = body['detail'] if 'detail' in body else None

                if op == 'process_spelunk':
                    spelunk_id = detail['spelunk_id'] if 'spelunk_id' in detail else None

                    spelunk_rec = get_spelunk_rec(spelunk_id)

                    if not spelunk_rec:
                        print (f'Spelunk {spelunk_id} not found, skipping')
                        return
                    
                    needs_processing = spelunk_rec_needs_transcript(spelunk_rec) or spelunk_rec_needs_summary(spelunk_rec)

                    if not needs_processing:
                        print (f'Spelunk {spelunk_id} does not need processing, skipping')
                        return

                    if spelunk_rec_needs_transcript(spelunk_rec):
                        try:
                            # first let's change the status to underway, and add a "started_at" timestamp
                            spelunk_rec['lenses']['transcript']['status'] = C_STATUS_UNDERWAY
                            spelunk_rec['lenses']['transcript']['started_at'] = int(time.time())
                            update_spelunk_rec(spelunk_rec)

                            # here we need to get the youtube transcript and write it to s3
                            s3_bucket = os.environ['bucket_name']

                            # don't need the transcript url here, but this will force create if it doesn't exist
                            get_youtube_transcript_url(spelunk_rec, s3_bucket)

                            # update the spelunk record to indicate that the transcript is ready
                            spelunk_rec['lenses']['transcript']['status'] = C_STATUS_READY

                            update_spelunk_rec(spelunk_rec)
                        except Exception as e:
                            print ('Failed to process spelunk: ' + exc_to_string(e))

                            spelunk_rec['lenses']['transcript']['status'] = C_STATUS_ERROR
                            spelunk_rec['lenses']['transcript']['message'] = exc_to_string(e)

                            try:
                                update_spelunk_rec(spelunk_rec)
                            except Exception as e:
                                print ('Failed to update spelunk record for error: ' + exc_to_string(e))
                                raise e
                    
                    if spelunk_rec_needs_summary(spelunk_rec):
                        try:
                            # first let's change the status to underway, and add a "started_at" timestamp
                            spelunk_rec['lenses']['summary']['status'] = C_STATUS_UNDERWAY
                            spelunk_rec['lenses']['summary']['started_at'] = int(time.time())
                            update_spelunk_rec(spelunk_rec)

                            # here we need to get the youtube transcript and write it to s3
                            s3_bucket = os.environ['bucket_name']

                            # don't need the transcript url here, but this will force create if it doesn't exist
                            get_youtube_summary_url(spelunk_rec, s3_bucket)

                            # update the spelunk record to indicate that the transcript is ready
                            spelunk_rec['lenses']['summary']['status'] = C_STATUS_READY

                            update_spelunk_rec(spelunk_rec)
                        except Exception as e:
                            print ('Failed to process spelunk: ' + exc_to_string(e))

                            spelunk_rec['lenses']['summary']['status'] = C_STATUS_ERROR
                            spelunk_rec['lenses']['summary']['message'] = exc_to_string(e)

                            try:
                                update_spelunk_rec(spelunk_rec)
                            except Exception as e:
                                print ('Failed to update spelunk record for error: ' + exc_to_string(e))
                                raise e
                else:
                    print ("Processing failed, Unknown operation: " + op) # can't retry this, it's just a permanent failure

            except Exception as e:
                msg = exc_to_string(e)
                print ("Error processing SQS message: " + msg)
                batchItemFailures.append({
                    'itemIdentifier': record['messageId'],
                })

        retval = {
            'batchItemFailures': batchItemFailures,
        }
        print ("Returning: " + json.dumps(retval, indent=2))
        return retval
    else:
        return {
            'statusCode': 403,
            'body': json.dumps('This lambda expects to process SQS messages')
        }
