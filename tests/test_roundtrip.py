"""Offline round trip: reading an ES edited in Word. The parts that need a drafted paper are covered by the
slow export walkthroughs; these check the reader and the rules on what may be taken."""
from io import BytesIO
from zipfile import ZipFile

import pytest

from backend.app.es2 import roundtrip
from backend.app.es2.export import MARKER

NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
DRAFT = '6ee4e8c557ca434ca013cae15b9a487f'


def docx(body, comments=None):
    out = BytesIO()
    with ZipFile(out, 'w') as package:
        package.writestr('word/document.xml', f'<w:document {NS}><w:body>{body}</w:body></w:document>')
        if comments:
            package.writestr('word/comments.xml', f'<w:comments {NS}>{comments}</w:comments>')
    return out.getvalue()


def paragraph(position, runs, extra=''):
    return (f'<w:p><w:pPr/>{extra}<w:bookmarkStart w:id="{90000 + position}" w:name="{MARKER}{DRAFT}_{position}"/>{runs}'
            f'<w:bookmarkEnd w:id="{90000 + position}"/></w:p>')


def test_marked_paragraphs_read_with_tracked_changes_taken_and_comments_placed():
    body = (paragraph(0, '<w:r><w:t xml:space="preserve">The facility is </w:t></w:r><w:del><w:r><w:delText>secured</w:delText></w:r></w:del>'
                         '<w:ins><w:r><w:t>fully secured</w:t></w:r></w:ins><w:r><w:t xml:space="preserve"> on the building. [1] [2]</w:t></w:r>')
            + '<w:p><w:r><w:t>An unmarked paragraph the analyst typed in Word.</w:t></w:r></w:p>'
            + paragraph(1, '<w:r><w:t>Repayment is from rental income. (see section 9)</w:t></w:r>', extra='<w:commentRangeStart w:id="7"/>'))
    notes = '<w:comment w:id="7" w:author="Sheryl"><w:p><w:r><w:t>Is this still right?</w:t></w:r></w:p></w:comment>'
    marked, comments = roundtrip.read(docx(body, notes))
    assert marked == {f'{MARKER}{DRAFT}_0': 'The facility is fully secured on the building. [1] [2]',
                      f'{MARKER}{DRAFT}_1': 'Repayment is from rental income. (see section 9)'}
    assert comments == [dict(author='Sheryl', text='Is this still right?', marker=f'{MARKER}{DRAFT}_1', quote='Repayment is from rental income. (see section 9)')]
    # Source markers and section references at the end of a paragraph are the system's, not wording.
    assert roundtrip.TRAILING_MARKS.sub('', marked[f'{MARKER}{DRAFT}_0']) == 'The facility is fully secured on the building.'
    assert roundtrip.TRAILING_MARKS.sub('', marked[f'{MARKER}{DRAFT}_1']) == 'Repayment is from rental income.'


def test_files_that_cannot_be_read_are_refused_with_a_reason():
    for content, reason in ((b'', 'empty'), (b'not a zip', 'not a Word'), (docx('').replace(b'word/document.xml', b'word/documenx.xml'), 'not a Word')):
        with pytest.raises(ValueError, match=reason):
            roundtrip.read(content)
    with pytest.raises(ValueError, match='definitions'):
        out = BytesIO()
        with ZipFile(out, 'w') as package:
            package.writestr('word/document.xml', f'<!DOCTYPE x [<!ENTITY a "b">]><w:document {NS}/>')
        roundtrip.read(out.getvalue())


def test_a_file_without_markers_or_from_another_paper_is_refused(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app.local import create_demo_app
    api = TestClient(create_demo_app(tmp_path, 'demo/synthetic_keppel'))
    case_id = api.get('/cases').json()[0]['id']
    send = lambda content: api.post(f'/cases/{case_id}/roundtrip/compare', content=content, headers={'Content-Type': 'application/octet-stream'})
    plain = send(docx('<w:p><w:r><w:t>Typed from scratch.</w:t></w:r></w:p>'))
    assert plain.status_code == 422 and 'No paragraph markers' in plain.json()['detail']
    other = send(docx(paragraph(0, '<w:r><w:t>From another paper.</w:t></w:r>')))
    assert other.status_code == 422 and 'different paper' in other.json()['detail']
    assert send(b'junk').status_code == 422 and api.post('/cases/unknown/roundtrip/compare', content=b'x').status_code == 404
    # Nothing to take is not an error, and takes nothing.
    assert api.post(f'/cases/{case_id}/roundtrip/apply', json=dict(actor='demo-ca')).json() == dict(saved_sections=[], threads_opened=0)


def test_protected_wording_is_recognised():
    assert roundtrip.protected(dict(kind='computed_summary')) and roundtrip.protected(dict(kind='claim', computed_value_ids=['x']))
    assert not roundtrip.protected(dict(kind='claim', text='Plain drafted wording.'))
