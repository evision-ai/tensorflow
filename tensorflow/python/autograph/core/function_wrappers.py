# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Support for wrapping converted functions bodies with auxiliary logic."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tensorflow.python.framework import auto_control_deps
from tensorflow.python.framework import ops
from tensorflow.python.framework import tensor_util
from tensorflow.python.util import nest


class FunctionScope(object):
  """Context manager that wraps the body of a converted function.

  This context manager handles various operations related to the scope of a
  function:
    * optional TF name scopes - these name scopes match the name of the
        function, for easy visualization in tensorBoard;
    * optional automatic control dependencies - this adds the same mechanism
        for control dependenecies that is used by `@tf.function`; it can be
        optionally enabled when using `tf.autograph.to_graph`;
  """

  def __init__(
      self, use_name_scope, function_scope_name, use_auto_deps):
    self.use_name_scope = use_name_scope
    if use_name_scope:
      self.name_scope = ops.name_scope(function_scope_name)

    self.use_auto_deps = use_auto_deps
    if use_auto_deps:
      self.autodeps_scope = auto_control_deps.AutomaticControlDependencies()
      self._return_value_marked = False

  def __enter__(self):
    if self.use_name_scope:
      self.name_scope.__enter__()
    if self.use_auto_deps:
      self.autodeps_scope.__enter__()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.use_name_scope:
      self.name_scope.__exit__(exc_type, exc_val, exc_tb)
    if self.use_auto_deps:
      self.autodeps_scope.__exit__(exc_type, exc_val, exc_tb)

  def mark_return_value(self, value):
    """Marks a value as returned from the function guarded by the scope."""
    if self.use_auto_deps:
      self._return_value_marked = True
      if value is None:
        # Unlike tf.function, we don't create dummy returns, to preserve Python
        # semantics. The user is responsible for adding a return value to the
        # top-level function.
        return None

      def _mark_return_if_tensor(t):
        if tensor_util.is_tensor(t):
          return self.autodeps_scope.mark_as_return(t)
        return t

      value = nest.map_structure(_mark_return_if_tensor, value)
    return value
