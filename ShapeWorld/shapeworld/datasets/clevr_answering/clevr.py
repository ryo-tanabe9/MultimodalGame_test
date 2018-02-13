from random import randrange
from shapeworld import util
from shapeworld.dataset import Dataset
from shapeworld.datasets import clevr_util


class CLEVR(Dataset):

    def __init__(self, directory, parts=None):
        world_size = tuple(next(clevr_util.images_iter(directory=directory, parts=parts, mode='train')).shape[:2])
        self.question_size = 0
        self.answer_size = 0
        vocabulary = set()
        for _, question, _, answer in clevr_util.questions_iter(directory=directory, parts=parts, mode='train'):
            self.question_size = max(self.question_size, len(question))
            self.answer_size = max(self.answer_size, len(answer))
            vocabulary.update(question)
            vocabulary.update(answer)
        vocabularies = dict(language=sorted(vocabulary))
        super(CLEVR, self).__init__(world_size=world_size, vectors=dict(question=self.question_size, answer=self.answer_size), vocabularies=vocabularies)
        self.clevr = {mode: clevr_util.clevr(directory=directory, parts=parts, mode=mode) for mode in ('train', 'validation', 'test')}

    @property
    def name(self):
        return 'clevr'

    @property
    def type(self):
        return 'clevr_answering'

    @property
    def values(self):
        return dict(world='world', world_model='model', question='alts(language)', question_length='alts(int)', question_model='alts(model)', answer='alts(language)', answer_length='alts(int)', alternatives='int')

    def generate(self, n, mode=None, noise_range=None, include_model=False, alternatives=False):
        assert noise_range is None or noise_range == 0.0
        batch = self.zero_batch(n, include_model=include_model, alternatives=alternatives)
        unknown = self.words['[UNKNOWN]']
        for i in range(n):
            try:
                world, world_model, questions, question_models, answers = next(self.clevr[mode])
            except StopIteration:
                if i > 0:
                    return {key: value[:i] for key, value in batch.items()}
                else:
                    return None
            batch['world'][i] = world
            if include_model:
                batch['world_model'][i] = world_model
            if alternatives:
                alts = len(questions)
                batch['alternatives'][i] = alts
                batch['question'][i].extend(batch['question'][i][0].copy() for _ in range(alts - 1))
                batch['answer'][i].extend(batch['answer'][i][0].copy() for _ in range(alts - 1))
                for a, (question, question_model, answer) in enumerate(zip(questions, question_models, answers)):
                    assert len(question) <= self.question_size
                    for w, word in enumerate(question):
                        batch['question'][i][a][w] = self.words.get(word, unknown)
                    batch['question_length'][i].append(len(question))
                    if include_model:
                        batch['question_model'][i].append(question_model)
                    assert len(answer) <= self.answer_size
                    for w, word in enumerate(answer):
                        batch['answer'][i][a][w] = self.words.get(word, unknown)
                    batch['answer_length'][i].append(len(answer))
            else:
                sample = randrange(len(questions))
                assert len(questions[sample]) <= self.question_size
                for j, word in enumerate(questions[sample]):
                    batch['question'][i][j] = self.words.get(word, unknown)
                batch['question_length'][i] = len(questions[sample])
                if include_model:
                    batch['question_model'][i] = question_models[sample]
                assert len(answers[sample]) <= self.answer_size
                for j, word in enumerate(answers[sample]):
                    batch['answer'][i][j] = self.words.get(word, unknown)
                batch['answer_length'][i] = len(answers[sample])
        return batch

    def get_html(self, generated):
        id2word = self.vocabulary(value_type='language')
        questions = generated['question']
        question_lengths = generated['question_length']
        answers = generated['answer']
        answer_lengths = generated['answer_length']
        data_html = list()
        for n, (question, question_length, answer, answer_length) in enumerate(zip(questions, question_lengths, answers, answer_lengths)):
            data_html.append('<div class="instance"><div class="world"><img src="world-{world}.bmp" alt="world-{world}.bmp"></div><div class="num"><p><b>({num})</b></p></div><div class="questions">'.format(world=n, num=(n + 1)))
            for question, question_length, answer, answer_length in zip(question, question_length, answer, answer_length):
                data_html.append('<p>{question}&ensp;&ndash;&ensp;{answer}</p>'.format(
                    question=util.tokens2string(id2word[word] for word in question[:question_length]),
                    answer=util.tokens2string(id2word[word] for word in answer[:answer_length])
                ))
            data_html.append('</div></div>')
        html = '<!DOCTYPE html><html><head><title>{dtype} {name}</title><style>.data{{width: 100%; height: 100%;}} .instance{{width: 100%; margin-top: 1px; margin-bottom: 1px; background-color: #CCCCCC;}} .world{{height: {world_height}px; display: inline-block; vertical-align: middle;}} .num{{display: inline-block; vertical-align: middle; margin-left: 10px;}} .questions{{display: inline-block; vertical-align: middle; margin-left: 10px;}}</style></head><body><div class="data">{data}</div></body></html>'.format(
            dtype=self.type,
            name=self.name,
            world_height=self.world_shape[0],
            data=''.join(data_html)
        )
        return html


dataset = CLEVR