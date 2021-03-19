# coding: utf-8

"""
Implementation of a mini-batch.
"""


class Batch:
    """Object for holding a batch of data with mask during training.
    Input is a batch from a torch text iterator.
    """

    def __init__(self, torch_batch, pad_index, use_cuda=False):
        """
        Create a new joey batch from a torch batch.
        This batch extends torch text's batch attributes with src and trg
        length, masks, number of non-padded tokens in trg.
        Furthermore, it can be sorted by src length.

        :param torch_batch:
        :param pad_index:
        :param use_cuda:
        """
        self.src, self.src_lengths = torch_batch.src
        self.src_mask = (self.src != pad_index).unsqueeze(1)
        self.nseqs = self.src.size(0)
        self.trg_input = None
        self.trg = None
        self.trg_mask = None
        self.trg_lengths = None
        self.ntokens = None
        self.use_cuda = use_cuda

        # I don't want to have to hard code every possible field name like this
        self.inflection = None
        self.inflection_lengths = None
        self.inflection_mask = None

        self.language = None

        if hasattr(torch_batch, "trg"):
            trg, trg_lengths = torch_batch.trg
            # trg_input is used for teacher forcing, last one is cut off
            self.trg_input = trg[:, :-1]
            self.trg_lengths = trg_lengths
            # trg is used for loss computation, shifted by one since BOS
            self.trg = trg[:, 1:]
            # we exclude the padded areas from the loss computation
            self.trg_mask = (self.trg_input != pad_index).unsqueeze(1)
            self.ntokens = (self.trg != pad_index).data.sum().item()

        if hasattr(torch_batch, "inflection"):
            self.inflection, self.inflection_lengths = torch_batch.inflection
            self.inflection_mask = (self.inflection != pad_index).unsqueeze(1)

        if hasattr(torch_batch, "language"):
            self.language = torch_batch.language

        if use_cuda:
            self._make_cuda()

    def _make_cuda(self):
        """
        Move the batch to GPU

        :return:
        """
        self.src = self.src.cuda()
        self.src_mask = self.src_mask.cuda()

        if self.trg_input is not None:
            self.trg_input = self.trg_input.cuda()
            self.trg = self.trg.cuda()
            self.trg_mask = self.trg_mask.cuda()

        # see above comment about hard coding
        if self.inflection is not None:
            self.inflection = self.inflection.cuda()
            self.inflection_lengths = self.inflection_lengths.cuda()
            self.inflection_mask = self.inflection_mask.cuda()

        if self.language is not None:
            self.language = self.language.cuda()

    def sort_by_src_lengths(self):
        """
        Sort by src length (descending) and return index to revert sort

        :return:
        """
        # this functionality is provided by BucketIterator, but it is
        # implemented here because BucketIterator does not provide the
        # rev_index, which is needed at evaluation time to get the examples
        # into corpus order
        _, perm_index = self.src_lengths.sort(0, descending=True)
        rev_index = [0]*perm_index.size(0)
        for new_pos, old_pos in enumerate(perm_index.cpu().numpy()):
            rev_index[old_pos] = new_pos

        sorted_src_lengths = self.src_lengths[perm_index]
        sorted_src = self.src[perm_index]
        sorted_src_mask = self.src_mask[perm_index]
        if self.trg_input is not None:
            sorted_trg_input = self.trg_input[perm_index]
            sorted_trg_lengths = self.trg_lengths[perm_index]
            sorted_trg_mask = self.trg_mask[perm_index]
            sorted_trg = self.trg[perm_index]
            self.trg_input = sorted_trg_input
            self.trg_mask = sorted_trg_mask
            self.trg_lengths = sorted_trg_lengths
            self.trg = sorted_trg

        if self.inflection is not None:
            sorted_inflection = self.inflection[perm_index]
            sorted_inflection_lengths = self.inflection_lengths[perm_index]
            sorted_inflection_mask = self.inflection_mask[perm_index]
            self.inflection = sorted_inflection
            self.inflection_lengths = sorted_inflection_lengths
            self.inflection_mask = sorted_inflection_mask

        if self.language is not None:
            self.language = self.language[perm_index]

        self.src = sorted_src
        self.src_lengths = sorted_src_lengths
        self.src_mask = sorted_src_mask

        if self.use_cuda:
            self._make_cuda()

        return rev_index
