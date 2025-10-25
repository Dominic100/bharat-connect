from validation_store import ValidationStore

def main():
    store = ValidationStore('./data/test_validation.db')
    row_id = store.save_report(
        url='https://example.com/feed',
        source='test',
        validator='ai',
        valid=True,
        report={'sample': 'report'},
        quality_score=95.5,
        run_id='smoke-run'
    )
    print('SAVED_ID', row_id)

if __name__ == '__main__':
    main()
