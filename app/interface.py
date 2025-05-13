# interface.py

from typing import Optional, List
from pydantic import BaseModel
from webview import Window
from tools.interface import expose
from typing import Dict, Set, List

class VoteConfig(BaseModel):
    mode: str  # "normal" or "series"
    vote_mode: bool

class VoteEntry(BaseModel):
    name: str
    count: int

class VoteRequest(BaseModel):
    user: str
    show_id: str

class VoteResults(BaseModel):
    results: List[VoteEntry]

class EmptyInput(BaseModel):
    pass


class API:
    def __init__(self):
        self.config = VoteConfig(mode="normal", vote_mode=False)
        self.user_votes: Dict[str, Set[str]] = {}  # username -> set of voted show ids
        self.votes: Dict[str, int] = {}  # show id -> count

    @expose(EmptyInput, VoteConfig)
    def get_config(self, _: EmptyInput) -> VoteConfig:
        return self.config

    @expose(VoteConfig, VoteConfig)
    def set_config(self, new_config: VoteConfig) -> VoteConfig:
        self.config = new_config
        return self.config

    @expose(EmptyInput, EmptyInput)
    def start_counting(self, _: EmptyInput) -> EmptyInput:
        self.user_votes.clear()
        self.votes.clear()
        return EmptyInput()

    @expose(EmptyInput, VoteResults)
    def end_counting(self, _: EmptyInput) -> VoteResults:
        # Finalize the vote and fire event to frontend with top N
        sorted_result = self._get_sorted_votes()
        #js_api.window.dispatchEvent(js.CustomEvent.new("ranking:update", {"detail": sorted_result.dict()}))
        return sorted_result

    @expose(VoteRequest, VoteResults)
    def receive_vote(self, vote_data: VoteRequest) -> VoteResults:
        username = vote_data.user
        show_id = vote_data.show_id

        if self.config.vote_mode:
            if username not in self.user_votes:
                self.user_votes[username] = set()
            if show_id in self.user_votes[username]:
                return self._get_sorted_votes()
            self.user_votes[username].add(show_id)

        self.votes[show_id] = self.votes.get(show_id, 0) + 1
        return self._get_sorted_votes()

    def _get_sorted_votes(self) -> VoteResults:
        sorted_list = list(self.votes.items())
        n = len(sorted_list)
        for i in range(n):
            for j in range(0, n - i - 1):
                if sorted_list[j][1] < sorted_list[j + 1][1]:
                    sorted_list[j], sorted_list[j + 1] = sorted_list[j + 1], sorted_list[j]
        return VoteResults(results=[VoteEntry(name=k, count=v) for k, v in sorted_list])
