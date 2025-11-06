/*!
 * Quill Editor v1.3.6
 * https://quilljs.com/
 * Copyright (c) 2014, Jason Chen
 * Copyright (c) 2013, salesforce.com
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1.  Redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer.
 *
 * 2.  Redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution.
 *
 * 3.  Neither the name of the copyright holder nor the names of its
 * contributors may be used to endorse or promote products derived
 * from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 * ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

(function (global, factory) {
	typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
	typeof define === 'function' && define.amd ? define(factory) :
	(global.Quill = factory());
}(this, (function () { 'use strict';

var global = typeof window !== 'undefined' ? window :
           typeof global !== 'undefined' ? global :
           typeof self !== 'undefined' ? self : {};
function commonjsRequire () {
	throw new Error('Dynamic requires are not supported');
}

var VENDOR_PREFIX = typeof navigator === 'object' && /WebKit/i.test(navigator.userAgent) ? '-webkit-' : '';

var DOCUMENT_NODE = typeof document === 'object' ? document.DOCUMENT_NODE : 9;
var ELEMENT_NODE = typeof document === 'object' ? document.ELEMENT_NODE : 1;
var TEXT_NODE = typeof document === 'object' ? document.TEXT_NODE : 3;

// MOVED SCOPE DEFINITION UP
var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; };
var __mb = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 134217728, 268435456, 536870912, 1073741824, 2147483648];
var Scope = {
  ATTRIBUTE: __mb[0],
  BLOT: __mb[1],
  INLINE_BLOT: __mb[2],
  BLOCK_BLOT: __mb[3],
  EMBED_BLOT: __mb[4],
  INLINE: __mb[2] | __mb[1] | __mb[0],
  BLOCK: __mb[3] | __mb[1] | __mb[0],
  EMBED: __mb[4] | __mb[1] | __mb[0],
  BLOCK_ATTRIBUTE: __mb[3] | __mb[0],
  INLINE_ATTRIBUTE: __mb[2] | __mb[0],
  EMBED_ATTRIBUTE: __mb[4] | __mb[0],
  ANY: __mb[0] | __mb[1] | __mb[2] | __mb[3] | __mb[4]
};
// END MOVED BLOCK

function isMac() {
  return typeof navigator === 'object' && /Mac/i.test(navigator.platform);
}

function isDescendant(node, container) {
  while (node != null) {
    if (node === container) return true;
    node = node.parentNode;
  }
  return false;
}

function isLine(node) {
  if (node == null) return false;
  return node.statics.scope === Scope.BLOCK_BLOT; // This was the line causing the error
}

function isWord(text) {
  var e = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

  if (e) {
    var preceded = /^\s{0,50000000}$/.test(text);
    return !preceded;
  } else {
    var followed = /^\s{0,50000000}$/.test(text);
    return !followed;
  }
}

function getSide(node, offset, direction) {
  if (offset === 0 && direction === 'left') return [node.previous, node.previous != null ? node.previous.length() : -1];
  if (offset === node.length() && direction === 'right') return [node.next, 0];
  return [node, offset];
}

function getWord(node, offset) {
  var e = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;

  if (node == null || node.statics.scope !== Scope.TEXT_BLOT) return [null, -1];
  var text = node.value();
  var start = offset;
  while (start > 0 && isWord(text.charAt(start - 1), e)) {
    start -= 1;
  }
  var end = offset;
  while (end < text.length && isWord(text.charAt(end), e)) {
    end += 1;
  }
  return [node, start, end];
}

function split(node, offset) {
  var after = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;

  if (node == null) return null;
  if (offset === 0) return node;
  if (offset === node.length()) return node.next;
  if (typeof node.split !== 'function') {
    if (after) {
      return node;
    } else {
      return node.previous;
    }
  }
  return node.split(offset, after);
}

function escapeText(text) {
  return text.replace(/[&<>"']/g, function (char) {
    return '&#' + char.charCodeAt(0) + ';';
  });
}

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

function required(name) {
  throw new Error('A class extending Parchment must implement ' + name);
}

var Parchment = function () {
  function Parchment(value) {
    _classCallCheck(this, Parchment);

    this.parent = null;
    this.children = new LinkedList();
    this.domNode = value;
    this.domNode[Registry.DATA_KEY] = { blot: this };
  }

  _createClass(Parchment, [{
    key: 'appendChild',
    value: function appendChild(other) {
      this.insertBefore(other);
    }
  }, {
    key: 'clone',
    value: function clone() {
      var domNode = this.domNode.cloneNode();
      return Registry.create(domNode);
    }
  }, {
    key: 'deleteAt',
    value: function deleteAt(index, length) {
      var _this = this;

      if (index === 0 && length === this.length()) {
        this.remove();
      } else {
        (function () {
          var target = _this.children.find(index, true);
          var offset = index - target.offset(_this);
          var remains = length;
          while (remains > 0 && target != null) {
            var targetLength = target.length();
            if (offset < targetLength) {
              if (offset + remains > targetLength) {
                target.deleteAt(offset, targetLength - offset);
                remains -= targetLength - offset;
              } else {
                target.deleteAt(offset, remains);
                remains = 0;
              }
            }
            target = target.next;
            offset = 0;
          }
        })();
      }
    }
  }, {
    key: 'format',
    value: function format(name, value) {
      if (this.statics.scope === Scope.BLOCK_BLOT) {
        if (name === this.statics.blotName && !value) {
          this.replaceWith(Parchment.DEFAULTS.block.blotName);
        }
      } else if (this.statics.scope === Scope.INLINE_BLOT) {
        if (name === this.statics.blotName && !value) {
          this.replaceWith(Parchment.DEFAULTS.inline.blotName);
        }
      }
    }
  }, {
    key: 'formatAt',
    value: function formatAt(index, length, name, value) {
      var _this2 = this;

      var target = this.children.find(index, true);
      var offset = index - target.offset(this);
      var remains = length;
      while (remains > 0 && target != null) {
        var targetLength = target.length();
        if (offset < targetLength) {
          if (offset + remains > targetLength) {
            target.formatAt(offset, targetLength - offset, name, value);
            remains -= targetLength - offset;
          } else {
            target.formatAt(offset, remains, name, value);
            remains = 0;
          }
        }
        target = target.next;
        offset = 0;
      }
      if (this.parent != null && this.statics.scope >= Scope.BLOCK_BLOT) {
        (function () {
          var target = _this2;
          while (target != null && target.statics.scope >= Scope.BLOCK_BLOT) {
            target.format(name, value);
            target = target.parent;
          }
        })();
      }
    }
  }, {
    key: 'formats',
    value: function formats() {
      return {};
    }
  }, {
    key: 'insertAt',
    value: function insertAt(index, value) {
      var target = this.children.find(index, true);
      var offset = index - target.offset(this);
      target.insertAt(offset, value);
    }
  }, {
    key: 'insertBefore',
    value: function insertBefore(other, ref) {
      if (other == null) return;
      if (other.parent != null) {
        other.parent.children.remove(other);
      }
      other.parent = this;
      this.children.insertBefore(other, ref);
      if (ref != null) {
        this.domNode.insertBefore(other.domNode, ref.domNode);
      } else {
        this.domNode.appendChild(other.domNode);
      }
    }
  }, {
    key: 'length',
    value: function length() {
      return this.children.length();
    }
  }, {
    key: 'moveChildren',
    value: function moveChildren(target) {
      var ref = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;

      this.children.forEach(function (child) {
        target.insertBefore(child, ref);
      });
    }
  }, {
    key: 'offset',
    value: function offset(root) {
      if (this.parent == null) return 0;
      if (root === this.parent) {
        return this.parent.children.offset(this);
      }
      return this.parent.offset(root) + this.parent.children.offset(this);
    }
  }, {
    key: 'optimize',
    value: function optimize() {
      if (this.children.length > 0) {
        this.children.optimize();
      }
    }
  }, {
    key: 'remove',
    value: function remove() {
      if (this.parent != null) {
        this.parent.children.remove(this);
      }
      if (this.domNode.parentNode != null) {
        this.domNode.parentNode.removeChild(this.domNode);
      }
    }
  }, {
    key: 'removeChild',
    value: function removeChild(child) {
      this.children.remove(child);
    }
  }, {
    key: 'replaceWith',
    value: function replaceWith(name, value) {
      var replacement = Registry.create(name, value);
      if (this.parent != null) {
        this.parent.insertBefore(replacement, this.next);
        this.remove();
      }
      return replacement;
    }
  }, {
    key: 'split',
    value: function split(index) {
      var force = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

      if (!force) {
        if (index === 0) return this;
        if (index === this.length()) return this.next;
      }
      var after = this.clone();
      if (this.parent != null) {
        this.parent.insertBefore(after, this.next);
      }
      this.children.split(index, after.children);
      return after;
    }
  }, {
    key: 'update',
    value: function update() {
      var mutations = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : [];
      // Nothing to do by default
    }
  }, {
    key: 'wrap',
    value: function wrap(name, value) {
      var wrapper = Registry.create(name, value);
      if (this.parent != null) {
        this.parent.insertBefore(wrapper, this.next);
      }
      wrapper.appendChild(this);
      return wrapper;
    }
  }]);

  return Parchment;
}();

Parchment.blotName = 'abstract';
Parchment.scope = null;
Parchment.tagName = 'abstract';
Parchment.DEFAULTS = {};

var LinkedList = function () {
  function LinkedList() {
    _classCallCheck(this, LinkedList);

    this.head = null;
    this.tail = null;
    this.length = 0;
  }

  _createClass(LinkedList, [{
    key: 'append',
    value: function append(node) {
      this.insertBefore(node, null);
    }
  }, {
    key: 'at',
    value: function at(index) {
      var _find2 = this.find(index);

      var node = _find2.node;

      return node;
    }
  }, {
    key: 'contains',
    value: function contains(node) {
      while (node != null) {
        if (node.parent === this) return true;
        node = node.parent;
      }
      return false;
    }
  }, {
    key: 'find',
    value: function find(index) {
      var inclusive = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

      var cur = this.head;
      var offset = 0;
      while (cur != null) {
        var length = cur.length();
        if (index < offset + length || inclusive && index === offset + length) {
          return { node: cur, offset: index - offset };
        }
        offset += length;
        cur = cur.next;
      }
      return { node: null, offset: -1 };
    }
  }, {
    key: 'forEach',
    value: function forEach(callback) {
      var cur = this.head;
      while (cur != null) {
        callback(cur);
        cur = cur.next;
      }
    }
  }, {
    key: 'forEachAt',
    value: function forEachAt(index, length, callback) {
      if (length <= 0) return;
      var _find3 = this.find(index);

      var startNode = _find3.node;
      var startOffset = _find3.offset;

      var cur = startNode;
      var curOffset = startOffset;
      var remaining = length;
      while (cur != null && remaining > 0) {
        var curLength = cur.length();
        if (curOffset < curLength) {
          var passLength = Math.min(curLength - curOffset, remaining);
          callback(cur, curOffset, passLength);
          remaining -= passLength;
        }
        cur = cur.next;
        curOffset = 0;
      }
    }
  }, {
    key: 'insertBefore',
    value: function insertBefore(node, ref) {
      if (node == null) return;
      node.parent = this;
      node.prev = ref != null ? ref.prev : this.tail;
      if (node.prev != null) {
        node.prev.next = node;
      } else {
        this.head = node;
      }
      node.next = ref;
      if (node.next != null) {
        node.next.prev = node;
      } else {
        this.tail = node;
      }
      this.length += 1;
    }
  }, {
    key: 'length',
    value: function length() {
      var sum = 0;
      this.forEach(function (node) {
        sum += node.length();
      });
      return sum;
    }
  }, {
    key: 'map',
    value: function map(callback) {
      var arr = [];
      this.forEach(function (node) {
        arr.push(callback(node));
      });
      return arr;
    }
  }, {
    key: 'moveAfter',
    value: function moveAfter(ref) {
      var _this3 = this;

      var after = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;

      var last = after;
      this.forEach(function (node) {
        ref.insertBefore(node, after);
        last = node;
      });
      return last;
    }
  }, {
    key: 'offset',
    value: function offset(node) {
      var cur = this.head;
      var offset = 0;
      while (cur != null) {
        if (cur === node) return offset;
        offset += cur.length();
        cur = cur.next;
      }
      return -1;
    }
  }, {
    key: 'optimize',
    value: function optimize() {
      var cur = this.head;
      while (cur != null) {
        var next = cur.next;
        if (next != null && typeof cur.merge === 'function' && cur.merge(next)) {
          cur.merge(next);
          next.remove();
        }
        cur = next;
      }
    }
  }, {
    key: 'reduce',
    value: function reduce(callback, memo) {
      this.forEach(function (node) {
        memo = callback(memo, node);
      });
      return memo;
    }
  }, {
    key: 'remove',
    value: function remove(node) {
      if (node.prev != null) {
        node.prev.next = node.next;
      } else {
        this.head = node.next;
      }
      if (node.next != null) {
        node.next.prev = node.prev;
      } else {
        this.tail = node.prev;
      }
      node.parent = null;
      node.prev = null;
      node.next = null;
      this.length -= 1;
    }
  }, {
    key: 'split',
    value: function split(index, after) {
      var _find4 = this.find(index);

      var cur = _find4.node;
      var offset = _find4.offset;

      var target = cur;
      while (target != null) {
        var next = target.next;
        this.remove(target);
        after.append(target);
        target = next;
      }
      if (cur != null) {
        var slice = cur.split(offset);
        if (slice != null) {
          after.insertBefore(slice, after.head);
        }
      }
    }
  }]);

  return LinkedList;
}();

var ParentBlot = function (_Parchment) {
  _inherits(ParentBlot, _Parchment);

  function ParentBlot(value) {
    _classCallCheck(this, ParentBlot);

    return _possibleConstructorReturn(this, (ParentBlot.__proto__ || Object.getPrototypeOf(ParentBlot)).call(this, value));
  }

  _createClass(ParentBlot, [{
    key: 'deleteAt',
    value: function deleteAt$$1(index, length) {
      if (index === 0 && length === this.length()) {
        this.remove();
      } else {
        this.children.deleteAt(index, length);
      }
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      this.children.formatAt(index, length, name, value);
    }
  }, {
    key: 'insertAt',
    value: function insertAt$$1(index, value, def) {
      var _children$find = this.children.find(index);

      var target = _children$find.node;
      var offset = _children$find.offset;

      if (target != null) {
        target.insertAt(offset, value, def);
      } else {
        var blot = def == null ? Registry.create('text', value) : Registry.create(def, value);
        this.appendChild(blot);
      }
    }
  }, {
    key: 'length',
    value: function length$$1() {
      return this.children.length();
    }
  }, {
    key: 'optimize',
    value: function optimize$$1() {
      _get(ParentBlot.prototype.__proto__ || Object.getPrototypeOf(ParentBlot.prototype), 'optimize', this).call(this);
      if (this.children.length > 0) {
        var first = this.children.head;
        this.children.forEach(function (child) {
          if (child.prev != null) {
            child.prev.next = child;
          }
        });
      }
    }
  }, {
    key: 'split',
    value: function split$$1(index) {
      var force = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

      if (!force) {
        if (index === 0) return this;
        if (index === this.length()) return this.next;
      }
      var after = this.clone();
      if (this.parent != null) {
        this.parent.insertBefore(after, this.next);
      }
      this.children.split(index, after.children);
      return after;
    }
  }, {
    key: 'update',
    value: function update$$1() {
      var mutations = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : [];

      var addedNodes = [];
      var removedNodes = [];
      mutations.forEach(function (mutation) {
        if (mutation.type === 'childList') {
          addedNodes.push.apply(addedNodes, mutation.addedNodes);
          removedNodes.push.apply(removedNodes, mutation.removedNodes);
        }
      });
      removedNodes.forEach(function (node) {
        var blot = Registry.find(node);
        if (blot == null) return;
        if (blot.parent != null) {
          blot.parent.removeChild(this);
        }
        blot.remove();
      }.bind(this));
      addedNodes.forEach(function (node) {
        if (node.parentNode == null) return;
        var blot = Registry.find(node);
        if (blot == null) {
          try {
            blot = Registry.create(node);
          } catch (e) {
            blot = Registry.create(Scope.INLINE);
          }
        }
        var ref = blot.next != null ? blot.next.domNode : null;
        if (blot.parent != null) {
          blot.parent.removeChild(this);
        }
        this.insertBefore(blot, ref);
      }.bind(this));
    }
  }]);

  return ParentBlot;
}(Parchment);

var LeafBlot = function (_Parchment) {
  _inherits(LeafBlot, _Parchment);

  function LeafBlot() {
    _classCallCheck(this, LeafBlot);

    return _possibleConstructorReturn(this, (LeafBlot.__proto__ || Object.getPrototypeOf(LeafBlot)).apply(this, arguments));
  }

  _createClass(LeafBlot, [{
    key: 'deleteAt',
    value: function deleteAt$$1(index, length) {
      this.value(this.value().slice(0, index) + this.value().slice(index + length));
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      if (index === 0 && length === this.length() && name === this.statics.blotName && !value) {
        this.replaceWith(Parchment.DEFAULTS.inline.blotName);
      }
    }
  }, {
    key: 'index',
    value: function index(node, offset) {
      return 0;
    }
  }, {
    key: 'insertAt',
    value: function insertAt$$1(index, value, def) {
      if (def == null) {
        this.value(this.value().slice(0, index) + value + this.value().slice(index));
      } else {
        var blot = Registry.create(def, value);
        var text = this.value();
        this.value(text.slice(0, index));
        this.parent.insertBefore(blot, this.next);
        blot.parent.insertBefore(Registry.create('text', text.slice(index)), blot.next);
        this.parent.optimize();
      }
    }
  }, {
    key: 'length',
    value: function length$$1() {
      return this.value().length;
    }
  }, {
    key: 'optimize',
    value: function optimize$$1() {
      if (this.length() === 0) {
        this.remove();
      }
    }
  }, {
    key: 'split',
    value: function split$$1(index) {
      var force = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

      if (!force) {
        if (index === 0) return this;
        if (index === this.length()) return this.next;
      }
      var after = this.clone();
      this.value(this.value().slice(0, index));
      after.value(after.value().slice(index));
      if (this.parent != null) {
        this.parent.insertBefore(after, this.next);
      }
      return after;
    }
  }, {
    key: 'update',
    value: function update$$1(mutations) {
      if (mutations.some(function (mutation) {
        return mutation.type === 'characterData';
      })) {
        this.value(this.domNode.data);
      }
    }
  }, {
    key: 'value',
    value: function value() {
      return this.domNode.data;
    }
  }]);

  return LeafBlot;
}(Parchment);

var _get = function get(object, property, receiver) { if (object === null) object = Function.prototype; var desc = Object.getOwnPropertyDescriptor(object, property); if (desc === undefined) { var parent = Object.getPrototypeOf(object); if (parent === null) { return undefined; } else { return get(parent, property, receiver); } } else if ("value" in desc) { return desc.value; } else { var getter = desc.get; if (getter === undefined) { return undefined; } return getter.call(receiver); } };

var ContainerBlot = function (_ParentBlot) {
  _inherits(ContainerBlot, _ParentBlot);

  function ContainerBlot() {
    _classCallCheck(this, ContainerBlot);

    return _possibleConstructorReturn(this, (ContainerBlot.__proto__ || Object.getPrototypeOf(ContainerBlot)).apply(this, arguments));
  }

  _createClass(ContainerBlot, [{
    key: 'format',
    value: function format$$1(name, value) {
      if (this.statics.allowedChildren != null && !this.statics.allowedChildren.some(function (blot) {
        return blot.blotName === name;
      })) {
        _get(ContainerBlot.prototype.__proto__ || Object.getPrototypeOf(ContainerBlot.prototype), 'format', this).call(this, name, value);
      }
    }
  }, {
    key: 'formats',
    value: function formats$$1() {
      return this.children.reduce(function (formats, child) {
        return Object.assign(formats, child.formats());
      }, {});
    }
  }, {
    key: 'insertBefore',
    value: function insertBefore$$1(blot, ref) {
      if (this.statics.allowedChildren != null && !this.statics.allowedChildren.some(function (child) {
        return blot instanceof child;
      })) {
        var newBlot = Registry.create(this.statics.defaultChild, blot.domNode);
        newBlot.moveChildren(blot);
        blot.remove();
        blot = newBlot;
      }
      _get(ContainerBlot.prototype.__proto__ || Object.getPrototypeOf(ContainerBlot.prototype), 'insertBefore', this).call(this, blot, ref);
    }
  }, {
    key: 'optimize',
    value: function optimize$$1() {
      _get(ContainerBlot.prototype.__proto__ || Object.getPrototypeOf(ContainerBlot.prototype), 'optimize', this).call(this);
      if (this.children.length > 0 && this.children.head.statics.scope !== this.statics.scope) {
        this.defaultChild != null ? this.wrap(this.defaultChild) : this.unwrap();
      }
    }
  }, {
    key: 'replaceWith',
    value: function replaceWith$$1(name, value) {
      var replacement = _get(ContainerBlot.prototype.__proto__ || Object.getPrototypeOf(ContainerBlot.prototype), 'replaceWith', this).call(this, name, value);
      if (replacement.statics.scope !== this.statics.scope) {
        this.moveChildren(replacement);
        this.remove();
      }
      return replacement;
    }
  }]);

  return ContainerBlot;
}(ParentBlot);

var BlockBlot = function (_ParentBlot) {
  _inherits(BlockBlot, _ParentBlot);

  function BlockBlot() {
    _classCallCheck(this, BlockBlot);

    return _possibleConstructorReturn(this, (BlockBlot.__proto__ || Object.getPrototypeOf(BlockBlot)).apply(this, arguments));
  }

  _createClass(BlockBlot, [{
    key: 'format',
    value: function format$$1(name, value) {
      var format = Registry.query(name, Scope.BLOCK_ATTRIBUTE);
      if (format != null) {
        this.attributes.attribute(format, value);
      } else {
        _get(BlockBlot.prototype.__proto__ || Object.getPrototypeOf(BlockBlot.prototype), 'format', this).call(this, name, value);
      }
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      var format = Registry.query(name, Scope.BLOCK_ATTRIBUTE);
      if (format != null) {
        this.attributes.attribute(format, value);
      }
      _get(BlockBlot.prototype.__proto__ || Object.getPrototypeOf(BlockBlot.prototype), 'formatAt', this).call(this, index, length, name, value);
    }
  }, {
    key: 'formats',
    value: function formats$$1() {
      return this.attributes.values();
    }
  }, {
    key: 'insertBefore',
    value: function insertBefore$$1(blot, ref) {
      if (blot.statics.scope > this.statics.scope) {
        var newBlot = Registry.create(this.statics.scope);
        newBlot.appendChild(blot);
        blot = newBlot;
      }
      _get(BlockBlot.prototype.__proto__ || Object.getPrototypeOf(BlockBlot.prototype), 'insertBefore', this).call(this, blot, ref);
    }
  }, {
    key: 'update',
    value: function update$$1(mutations) {
      _get(BlockBlot.prototype.__proto__ || Object.getPrototypeOf(BlockBlot.prototype), 'update', this).call(this, mutations);
      var attributes = mutations.filter(function (mutation) {
        return mutation.type === 'attributes';
      });
      if (attributes.length > 0) {
        this.attributes.build();
      }
    }
  }]);

  return BlockBlot;
}(ParentBlot);

BlockBlot.scope = Scope.BLOCK_BLOT;

var InlineBlot = function (_ParentBlot) {
  _inherits(InlineBlot, _ParentBlot);

  function InlineBlot() {
    _classCallCheck(this, InlineBlot);

    return _possibleConstructorReturn(this, (InlineBlot.__proto__ || Object.getPrototypeOf(InlineBlot)).apply(this, arguments));
  }

  _createClass(InlineBlot, [{
    key: 'format',
    value: function format$$1(name, value) {
      _get(InlineBlot.prototype.__proto__ || Object.getPrototypeOf(InlineBlot.prototype), 'format', this).call(this, name, value);
      if (Object.keys(this.formats()).length === 0) {
        this.replaceWith(Parchment.DEFAULTS.inline.blotName);
      }
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      if (this.formats()[name] != null || Registry.query(name, Scope.ATTRIBUTE)) {
        var blot = this.split(index);
        blot.split(length);
        blot.format(name, value);
      } else {
        _get(InlineBlot.prototype.__proto__ || Object.getPrototypeOf(InlineBlot.prototype), 'formatAt', this).call(this, index, length, name, value);
      }
    }
  }, {
    key: 'formats',
    value: function formats$$1() {
      return this.attributes.values();
    }
  }, {
    key: 'optimize',
    value: function optimize$$1() {
      _get(InlineBlot.prototype.__proto__ || Object.getPrototypeOf(InlineBlot.prototype), 'optimize', this).call(this);
      if (Object.keys(this.formats()).length === 0) {
        this.unwrap();
      }
    }
  }, {
    key: 'update',
    value: function update$$1(mutations) {
      _get(InlineBlot.prototype.__proto__ || Object.getPrototypeOf(InlineBlot.prototype), 'update', this).call(this, mutations);
      var attributes = mutations.filter(function (mutation) {
        return mutation.type === 'attributes';
      });
      if (attributes.length > 0) {
        this.attributes.build();
      }
    }
  }, {
    key: 'unwrap',
    value: function unwrap() {
      if (this.children.length > 0) {
        this.moveChildren(this.parent, this.next);
      }
      this.remove();
    }
  }]);

  return InlineBlot;
}(ParentBlot);

InlineBlot.scope = Scope.INLINE_BLOT;

var TextBlot = function (_LeafBlot) {
  _inherits(TextBlot, _LeafBlot);

  function TextBlot(value) {
    _classCallCheck(this, TextBlot);

    return _possibleConstructorReturn(this, (TextBlot.__proto__ || Object.getPrototypeOf(TextBlot)).call(this, value));
  }

  _createClass(TextBlot, [{
    key: 'merge',
    value: function merge(other) {
      if (other instanceof TextBlot) {
        this.value(this.value() + other.value());
        return true;
      }
      return false;
    }
  }, {
    key: 'value',
    value: function value$$1(value) {
      if (value != null) {
        this.domNode.data = value;
      }
      return this.domNode.data;
    }
  }], [{
    key: 'create',
    value: function create(value) {
      if (typeof value === 'string') {
        return document.createTextNode(value);
      } else {
        return _get(TextBlot.__proto__ || Object.getPrototypeOf(TextBlot), 'create', this).call(this, value);
      }
    }
  }, {
    key: 'value',
    value: function value(domNode) {
      return domNode.data;
    }
  }]);

  return TextBlot;
}(LeafBlot);

TextBlot.blotName = 'text';
TextBlot.scope = Scope.INLINE_BLOT;

var BreakBlot = function (_LeafBlot) {
  _inherits(BreakBlot, _LeafBlot);

  function BreakBlot() {
    _classCallCheck(this, BreakBlot);

    return _possibleConstructorReturn(this, (BreakBlot.__proto__ || Object.getPrototypeOf(BreakBlot)).apply(this, arguments));
  }

  _createClass(BreakBlot, [{
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      var blot = this.replaceWith(BreakBlot.blotName);
      blot.format(name, value);
    }
  }, {
    key: 'length',
    value: function length$$1() {
      return 1;
    }
  }, {
    key: 'value',
    value: function value$$1() {
      return '';
    }
  }]);

  return BreakBlot;
}(LeafBlot);

BreakBlot.blotName = 'break';
BreakBlot.scope = Scope.INLINE_BLOT;
BreakBlot.tagName = 'BR';

var EmbedBlot = function (_LeafBlot) {
  _inherits(EmbedBlot, _LeafBlot);

  function EmbedBlot() {
    _classCallCheck(this, EmbedBlot);

    return _possibleConstructorReturn(this, (EmbedBlot.__proto__ || Object.getPrototypeOf(EmbedBlot)).apply(this, arguments));
  }

  _createClass(EmbedBlot, [{
    key: 'deleteAt',
    value: function deleteAt$$1(index, length) {
      // Runner.js currently depends on this returning true
      return true;
    }
  }, {
    key: 'format',
    value: function format$$1(name, value) {
      var format = Registry.query(name, Scope.EMBED_ATTRIBUTE);
      if (format != null) {
        this.attributes.attribute(format, value);
      }
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      if (index === 0 && length === 1) {
        this.format(name, value);
      }
    }
  }, {
    key: 'formats',
    value: function formats$$1() {
      return this.attributes.values();
    }
  }, {
    key: 'index',
    value: function index$$1(node, offset) {
      return 1;
    }
  }, {
    key: 'insertAt',
    value: function insertAt$$1(index, value, def) {
      var blot = def == null ? Registry.create('text', value) : Registry.create(def, value);
      this.parent.insertBefore(blot, index === 0 ? this : this.next);
    }
  }, {
    key: 'length',
    value: function length$$1() {
      return 1;
    }
  }, {
    key: 'update',
    value: function update$$1(mutations) {
      _get(EmbedBlot.prototype.__proto__ || Object.getPrototypeOf(EmbedBlot.prototype), 'update', this).call(this, mutations);
      var attributes = mutations.filter(function (mutation) {
        return mutation.type === 'attributes';
      });
      if (attributes.length > 0) {
        this.attributes.build();
      }
    }
  }, {
    key: 'value',
    value: function value$$1() {
      return true;
    }
  }]);

  return EmbedBlot;
}(LeafBlot);

EmbedBlot.scope = Scope.INLINE_BLOT;

var Attributor = function () {
  function Attributor(attrName, keyName) {
    var options = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : {};

    _classCallCheck(this, Attributor);

    this.attrName = attrName;
    this.keyName = keyName;
    this.scope = options.scope || Scope.ATTRIBUTE;
    this.whitelist = options.whitelist || null;
  }

  _createClass(Attributor, [{
    key: 'add',
    value: function add(node, value) {
      if (!this.canAdd(node, value)) return;
      node.setAttribute(this.keyName, value);
    }
  }, {
    key: 'canAdd',
    value: function canAdd(node, value) {
      if (this.whitelist == null) return true;
      return this.whitelist.indexOf(value) !== -1;
    }
  }, {
    key: 'remove',
    value: function remove(node) {
      node.removeAttribute(this.keyName);
    }
  }, {
    key: 'value',
    value: function value(node) {
      var value = node.getAttribute(this.keyName);
      if (!this.canAdd(node, value)) {
        value = '';
      }
      return value;
    }
  }]);

  return Attributor;
}();

var ClassAttributor = function (_Attributor) {
  _inherits(ClassAttributor, _Attributor);

  function ClassAttributor() {
    _classCallCheck(this, ClassAttributor);

    return _possibleConstructorReturn(this, (ClassAttributor.__proto__ || Object.getPrototypeOf(ClassAttributor)).apply(this, arguments));
  }

  _createClass(ClassAttributor, [{
    key: 'add',
    value: function add(node, value) {
      if (!this.canAdd(node, value)) return;
      this.remove(node);
      node.classList.add('' + this.keyName + value);
    }
  }, {
    key: 'remove',
    value: function remove(node) {
      var _this12 = this;

      node.classList.forEach(function (name) {
        if (name.indexOf(_this12.keyName) === 0) {
          node.classList.remove(name);
        }
      });
    }
  }, {
    key: 'value',
    value: function value(node) {
      var _this13 = this;

      var value = node.classList.reduce(function (value, name) {
        if (name.indexOf(_this13.keyName) === 0) {
          return name.slice(_this13.keyName.length);
        } else {
          return value;
        }
      }, '');
      if (!this.canAdd(node, value)) {
        value = '';
      }
      return value;
    }
  }]);

  return ClassAttributor;
}(Attributor);

var StyleAttributor = function (_Attributor) {
  _inherits(StyleAttributor, _Attributor);

  function StyleAttributor() {
    _classCallCheck(this, StyleAttributor);

    return _possibleConstructorReturn(this, (StyleAttributor.__proto__ || Object.getPrototypeOf(StyleAttributor)).apply(this, arguments));
  }

  _createClass(StyleAttributor, [{
    key: 'add',
    value: function add(node, value) {
      if (!this.canAdd(node, value)) return;
      node.style[this.keyName] = value;
    }
  }, {
    key: 'remove',
    value: function remove(node) {
      node.style[this.keyName] = '';
      if (!node.getAttribute('style')) {
        node.removeAttribute('style');
      }
    }
  }, {
    key: 'value',
    value: function value(node) {
      var value = node.style[this.keyName];
      if (!this.canAdd(node, value)) {
        value = '';
      }
      return value;
    }
  }]);

  return StyleAttributor;
}(Attributor);

var AttributorStore = function () {
  function AttributorStore(domNode) {
    _classCallCheck(this, AttributorStore);

    this.domNode = domNode;
    this.attributes = {};
    this.build();
  }

  _createClass(AttributorStore, [{
    key: 'attribute',
    value: function attribute(attributor, value) {
      // verb
      if (value) {
        attributor.add(this.domNode, value);
      } else {
        attributor.remove(this.domNode);
      }
      this.build();
    }
  }, {
    key: 'build',
    value: function build() {
      var _this15 = this;

      this.attributes = {};
      var attributes = Registry.query(Scope.ATTRIBUTE);
      var classes = Array.from(this.domNode.classList);
      var styles = this.domNode.style || {};
      attributes.forEach(function (attr) {
        if (attr instanceof ClassAttributor) {
          classes.forEach(function (name) {
            if (name.indexOf(attr.keyName) === 0) {
              _this15.attributes[attr.attrName] = name.slice(attr.keyName.length);
            }
          });
        } else if (attr instanceof StyleAttributor) {
          if (styles[attr.keyName]) {
            _this15.attributes[attr.attrName] = styles[attr.keyName];
          }
        } else {
          if (_this15.domNode.hasAttribute(attr.keyName)) {
            _this15.attributes[attr.attrName] = _this15.domNode.getAttribute(attr.keyName);
          }
        }
      });
    }
  }, {
    key: 'copy',
    value: function copy(target) {
      var _this16 = this;

      Object.keys(this.attributes).forEach(function (key) {
        var attr = Registry.query(key, Scope.ATTRIBUTE);
        if (attr == null) return;
        attr.add(target.domNode, _this16.attributes[key]);
        target.build();
      });
    }
  }, {
    key: 'move',
    value: function move(target) {
      var _this17 = this;

      this.copy(target);
      Object.keys(this.attributes).forEach(function (key) {
        var attr = Registry.query(key, Scope.ATTRIBUTE);
        if (attr == null) return;
        attr.remove(_this17.domNode);
        _this17.build();
      });
    }
  }, {
    key: 'values',
    value: function values() {
      return Object.assign({}, this.attributes);
    }
  }]);

  return AttributorStore;
}();

// THIS BLOCK WAS MOVED UP.

var Registry = function () {
  function Registry() {
    _classCallCheck(this, Registry);

    this.attributes = {};
    this.classes = {};
    this.tags = {};
    this.types = {};
  }

  _createClass(Registry, [{
    key: 'create',
    value: function create(name, value) {
      var blotClass = this.query(name);
      if (blotClass == null) {
        throw new Error('Unable to create ' + name);
      }
      var domNode = void 0;
      if (value === undefined) {
        domNode = blotClass.create();
      } else if (typeof value === 'string') {
        domNode = blotClass.create(value);
      } else if (value instanceof Node) {
        domNode = value;
      } else {
        throw new Error('Unable to create ' + name + ' blot');
      }
      return new blotClass(domNode);
    }
  }, {
    key: 'find',
    value: function find(node) {
      var bubble = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

      if (node == null) return null;
      if (node[Registry.DATA_KEY] != null) return node[Registry.DATA_KEY].blot;
      if (bubble) return this.find(node.parentNode, bubble);
      return null;
    }
  }, {
    key: 'query',
    value: function query(query) {
      var scope = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : Scope.ANY;

      var match = void 0;
      if (typeof query === 'string') {
        match = this.types[query];
      } else if (query instanceof Node) {
        if (query.nodeType === TEXT_NODE) {
          match = this.types['text'];
        } else if (query.nodeType === ELEMENT_NODE) {
          match = this.tags[query.tagName];
        } else {
          return null;
        }
      } else if (typeof query === 'number') {
        if (query & Scope.BLOT & Scope.BLOCK) {
          match = this.types[Parchment.DEFAULTS.block.blotName];
        } else if (query & Scope.BLOT & Scope.INLINE) {
          match = this.types[Parchment.DEFAULTS.inline.blotName];
        }
      } else if ((typeof query === 'undefined' ? 'undefined' : _typeof(query)) === 'object') {
        match = this.attributes[query.attrName];
      }
      if (match == null) return null;
      if (typeof scope === 'number' && !(match.scope & scope)) return null;
      return match;
    }
  }, {
    key: 'register',
    value: function register(Definition) {
      if (Definition.blotName == null && Definition.attrName == null) {
        throw new Error('Invalid definition');
      }
      var name = Definition.blotName != null ? Definition.blotName : Definition.attrName;
      this.types[name] = Definition;
      if (typeof Definition.tagName === 'string') {
        this.tags[Definition.tagName.toUpperCase()] = Definition;
      } else if (Array.isArray(Definition.tagName)) {
        Definition.tagName.map(function (tagName) {
          return tagName.toUpperCase();
        }).forEach(function (tagName) {
          this.tags[tagName] = Definition;
        }.bind(this));
      } else if (_typeof(Definition.tagName) === 'object') {
        // TODO remove after deprecated
        console.warn && console.warn('Integer tag names are deprecated. Use strings instead.');
        this.tags[Definition.tagName] = Definition;
      }
      if (Definition.className != null) {
        this.classes[Definition.className] = Definition;
      }
      if (Definition.attrName != null) {
        this.attributes[Definition.attrName] = Definition;
      }
      return name;
    }
  }]);

  return Registry;
}();

Registry.DATA_KEY = '__blot';

var Block = function (_BlockBlot) {
  _inherits(Block, _BlockBlot);

  function Block(domNode) {
    _classCallCheck(this, Block);

    var _this18 = _possibleConstructorReturn(this, (Block.__proto__ || Object.getPrototypeOf(Block)).call(this, domNode));

    _this18.attributes = new AttributorStore(_this18.domNode);
    return _this18;
  }

  _createClass(Block, [{
    key: 'deleteAt',
    value: function deleteAt$$1(index, length) {
      _get(Block.prototype.__proto__ || Object.getPrototypeOf(Block.prototype), 'deleteAt', this).call(this, index, length);
      this.domNode.normalize();
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      if (Registry.query(name, Scope.INLINE_BLOT) != null) {
        _get(Block.prototype.__proto__ || Object.getPrototypeOf(Block.prototype), 'formatAt', this).call(this, index, length, name, value);
      } else if (length === 0) {
        this.format(name, value);
      } else {
        this.split(index).split(length);
        this.format(name, value);
      }
    }
  }, {
    key: 'insertAt',
    value: function insertAt$$1(index, value, def) {
      if (def != null && Registry.query(def, Scope.INLINE_BLOT) == null) {
        var _children$find2 = this.children.find(index);

        var target = _children$find2.node;
        var offset = _children$find2.offset;

        var after = this.split(index);
        var blot = Registry.create(def, value);
        after.parent.insertBefore(blot, after);
      } else {
        _get(Block.prototype.__proto__ || Object.getPrototypeOf(Block.prototype), 'insertAt', this).call(this, index, value, def);
      }
    }
  }, {
    key: 'insertBefore',
    value: function insertBefore$$1(blot, ref) {
      var head = this.children.head;
      if (head != null && head instanceof BreakBlot) {
        head.remove();
      }
      _get(Block.prototype.__proto__ || Object.getPrototypeOf(Block.prototype), 'insertBefore', this).call(this, blot, ref);
    }
  }, {
    key: 'length',
    value: function length$$1() {
      return _get(Block.prototype.__proto__ || Object.getPrototypeOf(Block.prototype), 'length', this).call(this) + 1; // Sentinel
    }
  }, {
    key: 'optimize',
    value: function optimize$$1() {
      _get(Block.prototype.__proto__ || Object.getPrototypeOf(Block.prototype), 'optimize', this).call(this);
      this.domNode.normalize();
    }
  }], [{
    key: 'create',
    value: function create() {
      var node = _get(Block.__proto__ || Object.getPrototypeOf(Block), 'create', this).call(this, this.tagName);
      node.appendChild(document.createElement(BreakBlot.tagName));
      return node;
    }
  }]);

  return Block;
}(BlockBlot);

Block.blotName = 'block';
Block.scope = Scope.BLOCK_BLOT;
Block.tagName = 'P';
Block.TAB = '  ';

var Inline = function (_InlineBlot) {
  _inherits(Inline, _InlineBlot);

  function Inline(domNode) {
    _classCallCheck(this, Inline);

    var _this19 = _possibleConstructorReturn(this, (Inline.__proto__ || Object.getPrototypeOf(Inline)).call(this, domNode));

    _this19.attributes = new AttributorStore(_this19.domNode);
    return _this19;
  }

  _createClass(Inline, null, [{
    key: 'create',
    value: function create() {
      var node = _get(Inline.__proto__ || Object.getPrototypeOf(Inline), 'create', this).call(this, this.tagName);
      this.keys().forEach(function (name) {
        var attr = Registry.query(name, Scope.ATTRIBUTE);
        if (attr != null) {
          attr.add(node, attr.value(node));
        }
      });
      return node;
    }
  }, {
    key: 'keys',
    value: function keys(node) {
      return (node.getAttribute('class') || '').split(/\s+/);
    }
  }]);

  return Inline;
}(InlineBlot);

Inline.blotName = 'inline';
Inline.scope = Scope.INLINE_BLOT;
Inline.tagName = 'SPAN';
Inline.TAB = '\t';

var Scroll = function (_ContainerBlot) {
  _inherits(Scroll, _ContainerBlot);

  function Scroll(node) {
    _classCallCheck(this, Scroll);

    return _possibleConstructorReturn(this, (Scroll.__proto__ || Object.getPrototypeOf(Scroll)).call(this, node));
  }

  _createClass(Scroll, [{
    key: 'deleteAt',
    value: function deleteAt$$1(index, length) {
      _get(Scroll.prototype.__proto__ || Object.getPrototypeOf(Scroll.prototype), 'deleteAt', this).call(this, index, length);
      this.optimize();
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      _get(Scroll.prototype.__proto__ || Object.getPrototypeOf(Scroll.prototype), 'formatAt', this).call(this, index, length, name, value);
      this.optimize();
    }
  }, {
    key: 'insertAt',
    value: function insertAt$$1(index, value, def) {
      _get(Scroll.prototype.__proto__ || Object.getPrototypeOf(Scroll.prototype), 'insertAt', this).call(this, index, value, def);
      this.optimize();
    }
  }, {
    key: 'optimize',
    value: function optimize$$1() {
      _get(Scroll.prototype.__proto__ || Object.getPrototypeOf(Scroll.prototype), 'optimize', this).call(this);
      if (this.children.length > 0 && this.children.tail.statics.scope !== Scope.BLOCK_BLOT) {
        this.appendChild(Registry.create(Scope.BLOCK_BLOT & Scope.BLOT));
      }
    }
  }]);

  return Scroll;
}(ContainerBlot);

Scroll.blotName = 'scroll';
Scroll.scope = Scope.BLOCK_BLOT;
Scroll.tagName = 'DIV';
Scroll.defaultChild = 'block';
Scroll.allowedChildren = [Block, ContainerBlot];

Parchment.DEFAULTS = {
  block: {
    blotName: 'block',
    scope: Scope.BLOCK_BLOT
  },
  inline: {
    blotName: 'inline',
    scope: Scope.INLINE_BLOT
  }
};

Registry.register(Scroll, Block, Inline, TextBlot, BreakBlot);

// THIS IS THE BLOCK THAT WAS MOVED
var ALIGNS = {
  'center': null,
  'right': null,
  'justify': null
};

var Align = new ClassAttributor('align', 'ql-align-', {
  scope: Scope.BLOCK_ATTRIBUTE,
  whitelist: Object.keys(ALIGNS)
});

var Background = new StyleAttributor('background', 'background-color', {
  scope: Scope.INLINE_ATTRIBUTE,
  whitelist: ['rgb(0, 0, 0)', 'rgb(230, 0, 0)', 'rgb(255, 153, 0)', 'rgb(255, 255, 0)', 'rgb(0, 138, 0)', 'rgb(0, 102, 204)', 'rgb(153, 51, 255)', 'rgb(255, 255, 255)', 'rgb(250, 204, 204)', 'rgb(255, 235, 204)', 'rgb(255, 255, 204)', 'rgb(204, 232, 204)', 'rgb(204, 224, 245)', 'rgb(235, 214, 255)', 'rgb(187, 187, 187)', 'rgb(240, 102, 102)', 'rgb(255, 194, 102)', 'rgb(255, 255, 102)', 'rgb(102, 185, 102)', 'rgb(102, 163, 224)', 'rgb(194, 133, 255)', 'rgb(136, 136, 136)', 'rgb(161, 0, 0)', 'rgb(178, 107, 0)', 'rgb(178, 178, 0)', 'rgb(0, 97, 0)', 'rgb(0, 71, 142)', 'rgb(107, 36, 178)', 'rgb(68, 68, 68)', 'rgb(92, 0, 0)', 'rgb(102, 61, 0)', 'rgb(102, 102, 0)', 'rgb(0, 55, 0)', 'rgb(0, 41, 82)', 'rgb(61, 20, 102)']
});

var Color = new StyleAttributor('color', 'color', {
  scope: Scope.INLINE_ATTRIBUTE,
  whitelist: ['rgb(0, 0, 0)', 'rgb(230, 0, 0)', 'rgb(255, 153, 0)', 'rgb(255, 255, 0)', 'rgb(0, 138, 0)', 'rgb(0, 102, 204)', 'rgb(153, 51, 255)', 'rgb(255, 255, 255)', 'rgb(250, 204, 204)', 'rgb(255, 235, 204)', 'rgb(255, 255, 204)', 'rgb(204, 232, 204)', 'rgb(204, 224, 245)', 'rgb(235, 214, 255)', 'rgb(187, 187, 187)', 'rgb(240, 102, 102)', 'rgb(255, 194, 102)', 'rgb(255, 255, 102)', 'rgb(102, 185, 102)', 'rgb(102, 163, 224)', 'rgb(194, 133, 255)', 'rgb(136, 136, 136)', 'rgb(161, 0, 0)', 'rgb(178, 107, 0)', 'rgb(178, 178, 0)', 'rgb(0, 97, 0)', 'rgb(0, 71, 142)', 'rgb(107, 36, 178)', 'rgb(68, 68, 68)', 'rgb(92, 0, 0)', 'rgb(102, 61, 0)', 'rgb(102, 102, 0)', 'rgb(0, 55, 0)', 'rgb(0, 41, 82)', 'rgb(61, 20, 102)']
});

var Direction = new ClassAttributor('direction', 'ql-direction-', {
  scope: Scope.BLOCK_ATTRIBUTE,
  whitelist: ['rtl']
});
Direction.add = function (node, value) {
  if (value === 'rtl') {
    _get(Direction.__proto__ || Object.getPrototypeOf(Direction), 'add', this).call(this, node, 'rtl');
    node.setAttribute('dir', 'rtl');
  } else {
    this.remove(node);
  }
};
Direction.remove = function (node) {
  _get(Direction.__proto__ || Object.getPrototypeOf(Direction), 'remove', this).call(this, node);
  node.removeAttribute('dir');
};

var Font = new StyleAttributor('font', 'font-family', {
  scope: Scope.INLINE_ATTRIBUTE,
  whitelist: ['serif', 'monospace']
});

var Size = new StyleAttributor('size', 'font-size', {
  scope: Scope.INLINE_ATTRIBUTE,
  whitelist: ['small', 'large', 'huge']
});

var Bold = function (_Inline) {
  _inherits(Bold, _Inline);

  function Bold() {
    _classCallCheck(this, Bold);

    return _possibleConstructorReturn(this, (Bold.__proto__ || Object.getPrototypeOf(Bold)).apply(this, arguments));
  }

  _createClass(Bold, null, [{
    key: 'create',
    value: function create$$1() {
      return _get(Bold.__proto__ || Object.getPrototypeOf(Bold), 'create', this).call(this, this.tagName);
    }
  }]);

  return Bold;
}(Inline);

Bold.blotName = 'bold';
Bold.tagName = 'STRONG';

var Italic = function (_Inline) {
  _inherits(Italic, _Inline);

  function Italic() {
    _classCallCheck(this, Italic);

    return _possibleConstructorReturn(this, (Italic.__proto__ || Object.getPrototypeOf(Italic)).apply(this, arguments));
  }

  _createClass(Italic, null, [{
    key: 'create',
    value: function create$$1() {
      return _get(Italic.__proto__ || Object.getPrototypeOf(Italic), 'create', this).call(this, this.tagName);
    }
  }]);

  return Italic;
}(Inline);

Italic.blotName = 'italic';
Italic.tagName = 'EM';

var Link = function (_Inline) {
  _inherits(Link, _Inline);

  function Link(domNode) {
    _classCallCheck(this, Link);

    var _this24 = _possibleConstructorReturn(this, (Link.__proto__ || Object.getPrototypeOf(Link)).call(this, domNode));

    _this24.domNode.addEventListener('mouseover', Link.handleMouseover);
    _this24.domNode.addEventListener('mouseout', Link.handleMouseout);
    return _this24;
  }

  _createClass(Link, [{
    key: 'format',
    value: function format$$1(name, value) {
      if (name === Link.blotName && !value) {
        this.domNode.removeEventListener('mouseover', Link.handleMouseover);
        this.domNode.removeEventListener('mouseout', Link.handleMouseout);
      }
      _get(Link.prototype.__proto__ || Object.getPrototypeOf(Link.prototype), 'format', this).call(this, name, value);
    }
  }, {
    key: 'formats',
    value: function formats$$1() {
      var formats = _get(Link.prototype.__proto__ || Object.getPrototypeOf(Link.prototype), 'formats', this).call(this);
      formats[Link.blotName] = Link.formats(this.domNode);
      return formats;
    }
  }], [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(Link.__proto__ || Object.getPrototypeOf(Link), 'create', this).call(this, this.tagName);
      node.setAttribute('href', value);
      node.setAttribute('target', '_blank');
      return node;
    }
  }, {
    key: 'formats',
    value: function formats(domNode) {
      return domNode.getAttribute('href');
    }
  }, {
    key: 'handleMouseover',
    value: function handleMouseover(evt) {
      if (this.tooltip == null) return;
      var preview = this.tooltip.root.querySelector('a.ql-preview');
      preview.textContent = evt.target.getAttribute('href');
    }
  }, {
    key: 'handleMouseout',
    value: function handleMouseout(evt) {
      if (this.tooltip == null) return;
      var preview = this.tooltip.root.querySelector('a.ql-preview');
      preview.textContent = '';
    }
  }]);

  return Link;
}(Inline);

Link.blotName = 'link';
Link.tagName = 'A';

var Script = function (_Inline) {
  _inherits(Script, _Inline);

  function Script() {
    _classCallCheck(this, Script);

    return _possibleConstructorReturn(this, (Script.__proto__ || Object.getPrototypeOf(Script)).apply(this, arguments));
  }

  _createClass(Script, null, [{
    key: 'create',
    value: function create$$1(value) {
      if (value === 'super') {
        return _get(Script.__proto__ || Object.getPrototypeOf(Script), 'create', this).call(this, 'SUP');
      } else if (value === 'sub') {
        return _get(Script.__proto__ || Object.getPrototypeOf(Script), 'create', this).call(this, 'SUB');
      } else {
        return _get(Script.__proto__ || Object.getPrototypeOf(Script), 'create', this).call(this, value);
      }
    }
  }, {
    key: 'formats',
    value: function formats(domNode) {
      if (domNode.tagName === 'SUB') return 'sub';
      if (domNode.tagName === 'SUP') return 'super';
      return undefined;
    }
  }]);

  return Script;
}(Inline);

Script.blotName = 'script';
Script.tagName = ['SUB', 'SUP'];

var Strike = function (_Inline) {
  _inherits(Strike, _Inline);

  function Strike() {
    _classCallCheck(this, Strike);

    return _possibleConstructorReturn(this, (Strike.__proto__ || Object.getPrototypeOf(Strike)).apply(this, arguments));
  }

  _createClass(Strike, null, [{
    key: 'create',
    value: function create$$1() {
      return _get(Strike.__proto__ || Object.getPrototypeOf(Strike), 'create', this).call(this, this.tagName);
    }
  }]);

  return Strike;
}(Inline);

Strike.blotName = 'strike';
Strike.tagName = 'S';

var Underline = function (_Inline) {
  _inherits(Underline, _Inline);

  function Underline() {
    _classCallCheck(this, Underline);

    return _possibleConstructorReturn(this, (Underline.__proto__ || Object.getPrototypeOf(Underline)).apply(this, arguments));
  }

  _createClass(Underline, null, [{
    key: 'create',
    value: function create$$1() {
      return _get(Underline.__proto__ || Object.getPrototypeOf(Underline), 'create', this).call(this, this.tagName);
    }
  }]);

  return Underline;
}(Inline);

Underline.blotName = 'underline';
Underline.tagName = 'U';

var Blockquote = function (_Block) {
  _inherits(Blockquote, _Block);

  function Blockquote() {
    _classCallCheck(this, Blockquote);

    return _possibleConstructorReturn(this, (Blockquote.__proto__ || Object.getPrototypeOf(Blockquote)).apply(this, arguments));
  }

  return Blockquote;
}(Block);

Blockquote.blotName = 'blockquote';
Blockquote.tagName = 'BLOCKQUOTE';

var Header = function (_Block) {
  _inherits(Header, _Block);

  function Header() {
    _classCallCheck(this, Header);

    return _possibleConstructorReturn(this, (Header.__proto__ || Object.getPrototypeOf(Header)).apply(this, arguments));
  }

  _createClass(Header, null, [{
    key: 'create',
    value: function create$$1(value) {
      return _get(Header.__proto__ || Object.getPrototypeOf(Header), 'create', this).call(this, 'H' + value);
    }
  }, {
    key: 'formats',
    value: function formats(domNode) {
      return domNode.tagName.slice(1);
    }
  }]);

  return Header;
}(Block);

Header.blotName = 'header';
Header.tagName = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'];

var Indent = new ClassAttributor('indent', 'ql-indent-', {
  scope: Scope.BLOCK_ATTRIBUTE,
  whitelist: [1, 2, 3, 4, 5, 6, 7, 8, 9]
});
Indent.add = function (node, value) {
  if (value === 0) {
    this.remove(node);
  } else {
    _get(Indent.__proto__ || Object.getPrototypeOf(Indent), 'add', this).call(this, node, value);
  }
};

var List = function (_Block) {
  _inherits(List, _Block);

  function List() {
    _classCallCheck(this, List);

    return _possibleConstructorReturn(this, (List.__proto__ || Object.getPrototypeOf(List)).apply(this, arguments));
  }

  _createClass(List, null, [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(List.__proto__ || Object.getPrototypeOf(List), 'create', this).call(this, this.tagName);
      if (value === 'checked' || value === 'unchecked') {
        node.setAttribute('data-checked', value === 'checked');
      }
      return node;
    }
  }, {
    key: 'formats',
    value: function formats(domNode) {
      if (domNode.hasAttribute('data-checked')) {
        return domNode.getAttribute('data-checked') === 'true' ? 'checked' : 'unchecked';
      }
      return undefined;
    }
  }]);

  return List;
}(Block);

List.blotName = 'list';
List.tagName = 'LI';

var CodeBlock = function (_Block) {
  _inherits(CodeBlock, _Block);

  function CodeBlock() {
    _classCallCheck(this, CodeBlock);

    return _possibleConstructorReturn(this, (CodeBlock.__proto__ || Object.getPrototypeOf(CodeBlock)).apply(this, arguments));
  }

  _createClass(CodeBlock, [{
    key: 'deleteAt',
    value: function deleteAt$$1(index, length) {
      var _children$find3 = this.children.find(index + length);

      var endBlot = _children$find3.node;
      var endOffset = _children$find3.offset;

      _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'deleteAt', this).call(this, index, length);
      if (endBlot != null && endBlot.next == null && endOffset > 0) {
        this.appendChild(Registry.create('text', '\n'));
      }
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      if (index + length === this.length()) {
        _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'formatAt', this).call(this, index, length - 1, name, value);
      } else {
        _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'formatAt', this).call(this, index, length, name, value);
      }
    }
  }, {
    key: 'insertAt',
    value: function insertAt$$1(index, value, def) {
      if (index >= this.length() - 1) {
        // Exclude newline
        _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'insertAt', this).call(this, index, value, def);
      } else {
        var parts = value.split('\n');
        if (parts.length > 1) {
          _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'insertAt', this).call(this, index, parts[0], def);
          var after = this.split(index + parts[0].length);
          parts.slice(1).forEach(function (part) {
            var blot = Registry.create(CodeBlock.blotName);
            blot.insertAt(0, part);
            after.parent.insertBefore(blot, after);
          });
        } else {
          _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'insertAt', this).call(this, index, value, def);
        }
      }
    }
  }, {
    key: 'length',
    value: function length$$1() {
      return _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'length', this).call(this);
    }
  }], [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(CodeBlock.__proto__ || Object.getPrototypeOf(CodeBlock), 'create', this).call(this, this.tagName);
      node.setAttribute('spellcheck', false);
      return node;
    }
  }]);

  return CodeBlock;
}(Block);

CodeBlock.blotName = 'code-block';
CodeBlock.tagName = 'PRE';

var BlockContainer = function (_ContainerBlot) {
  _inherits(BlockContainer, _ContainerBlot);

  function BlockContainer() {
    _classCallCheck(this, BlockContainer);

    return _possibleConstructorReturn(this, (BlockContainer.__proto__ || Object.getPrototypeOf(BlockContainer)).apply(this, arguments));
  }

  return BlockContainer;
}(ContainerBlot);

BlockContainer.blotName = 'container';
BlockContainer.scope = Scope.BLOCK_BLOT;
BlockContainer.tagName = 'DIV';
BlockContainer.defaultChild = 'block';
BlockContainer.allowedChildren = [Block];

// THIS IS THE DUPLICATE BLOCK THAT MUST BE DELETED
// (The error at line 1635 is inside this block)
/*
var ALIGNS = {
  'center': null,
  'right': null,
  'justify': null
};
var Align = new ClassAttributor('align', 'ql-align-', {
  scope: Scope.BLOCK_ATTRIBUTE,
  whitelist: Object.keys(ALIGNS)
});
var Background = new StyleAttributor('background', 'background-color', {
  scope: Scope.INLINE_ATTRIBUTE,
  whitelist: ['rgb(0, 0, 0)', 'rgb(230, 0, 0)', 'rgb(255, 153, 0)', 'rgb(255, 255, 0)', 'rgb(0, 138, 0)', 'rgb(0, 102, 204)', 'rgb(153, 51, 255)', 'rgb(255, 255, 255)', 'rgb(250, 204, 204)', 'rgb(255, 235, 204)', 'rgb(255, 255, 204)', 'rgb(204, 232, 204)', 'rgb(204, 224, 245)', 'rgb(235, 214, 255)', 'rgb(187, 187, 187)', 'rgb(240, 102, 102)', 'rgb(255, 194, 102)', 'rgb(255, 255, 102)', 'rgb(102, 185, 102)', 'rgb(102, 163, 224)', 'rgb(194, 133, 255)', 'rgb(136, 136, 136)', 'rgb(161, 0, 0)', 'rgb(178, 107, 0)', 'rgb(178, 178, 0)', 'rgb(0, 97, 0)', 'rgb(0, 71, 142)', 'rgb(107, 36, 178)', 'rgb(68, 68, 68)', 'rgb(92, 0, 0)', 'rgb(102, 61, 0)', 'rgb(102, 102, 0)', 'rgb(0, 55, 0)', 'rgb(0, 41, 82)', 'rgb(61, 20, 102)']
});
var Color = new StyleAttributor('color', 'color', {
  scope: Scope.INLINE_ATTRIBUTE,
  whitelist: ['rgb(0, 0, 0)', 'rgb(230, 0, 0)', 'rgb(255, 153, 0)', 'rgb(255, 255, 0)', 'rgb(0, 138, 0)', 'rgb(0, 102, 204)', 'rgb(153, 51, 255)', 'rgb(255, 255, 255)', 'rgb(250, 204, 204)', 'rgb(255, 235, 204)', 'rgb(255, 255, 204)', 'rgb(204, 232, 204)', 'rgb(204, 224, 245)', 'rgb(235, 214, 255)', 'rgb(187, 187, 187)', 'rgb(240, 102, 102)', 'rgb(255, 194, 102)', 'rgb(255, 255, 102)', 'rgb(102, 185, 102)', 'rgb(102, 163, 224)', 'rgb(194, 133, 255)', 'rgb(136, 136, 136)', 'rgb(161, 0, 0)', 'rgb(178, 107, 0)', 'rgb(178, 178, 0)', 'rgb(0, 97, 0)', 'rgb(0, 71, 142)', 'rgb(107, 36, 178)', 'rgb(68, 68, 68)', 'rgb(92, 0, 0)', 'rgb(102, 61, 0)', 'rgb(102, 102, 0)', 'rgb(0, 55, 0)', 'rgb(0, 41, 82)', 'rgb(61, 20, 102)']
});
var Direction = new ClassAttributor('direction', 'ql-direction-', {
  scope: Scope.BLOCK_ATTRIBUTE,
  whitelist: ['rtl']
});
Direction.add = function (node, value) {
  if (value === 'rtl') {
    _get(Direction.__proto__ || Object.getPrototypeOf(Direction), 'add', this).call(this, node, 'rtl');
    node.setAttribute('dir', 'rtl');
  } else {
    this.remove(node);
  }
};
Direction.remove = function (node) {
  _get(Direction.__proto__ || Object.getPrototypeOf(Direction), 'remove', this).call(this, node);
  node.removeAttribute('dir');
};
var Font = new StyleAttributor('font', 'font-family', {
  scope: Scope.INLINE_ATTRIBUTE,
  whitelist: ['serif', 'monospace']
});
var Size = new StyleAttributor('size', 'font-size', {
  scope: Scope.INLINE_ATTRIBUTE,
  whitelist: ['small', 'large', 'huge']
});
var Bold = function (_Inline) {
  _inherits(Bold, _Inline);
  function Bold() {
    _classCallCheck(this, Bold);
    return _possibleConstructorReturn(this, (Bold.__proto__ || Object.getPrototypeOf(Bold)).apply(this, arguments));
  }
  _createClass(Bold, null, [{
    key: 'create',
    value: function create$$1() {
      return _get(Bold.__proto__ || Object.getPrototypeOf(Bold), 'create', this).call(this, this.tagName);
    }
  }]);
  return Bold;
}(Inline);
Bold.blotName = 'bold';
Bold.tagName = 'STRONG';
var Italic = function (_Inline) {
  _inherits(Italic, _Inline);
  function Italic() {
    _classCallCheck(this, Italic);
    return _possibleConstructorReturn(this, (Italic.__proto__ || Object.getPrototypeOf(Italic)).apply(this, arguments));
  }
  _createClass(Italic, null, [{
    key: 'create',
    value: function create$$1() {
      return _get(Italic.__proto__ || Object.getPrototypeOf(Italic), 'create', this).call(this, this.tagName);
    }
  }]);
  return Italic;
}(Inline);
Italic.blotName = 'italic';
Italic.tagName = 'EM';
var Link = function (_Inline) {
  _inherits(Link, _Inline);
  function Link(domNode) {
    _classCallCheck(this, Link);
    var _this24 = _possibleConstructorReturn(this, (Link.__proto__ || Object.getPrototypeOf(Link)).call(this, domNode));
    _this24.domNode.addEventListener('mouseover', Link.handleMouseover);
    _this24.domNode.addEventListener('mouseout', Link.handleMouseout);
    return _this24;
  }
  _createClass(Link, [{
    key: 'format',
    value: function format$$1(name, value) {
      if (name === Link.blotName && !value) {
        this.domNode.removeEventListener('mouseover', Link.handleMouseover);
        this.domNode.removeEventListener('mouseout', Link.handleMouseout);
      }
      _get(Link.prototype.__proto__ || Object.getPrototypeOf(Link.prototype), 'format', this).call(this, name, value);
    }
  }, {
    key: 'formats',
    value: function formats$$1() {
      var formats = _get(Link.prototype.__proto__ || Object.getPrototypeOf(Link.prototype), 'formats', this).call(this);
      formats[Link.blotName] = Link.formats(this.domNode);
      return formats;
    }
  }], [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(Link.__proto__ || Object.getPrototypeOf(Link), 'create', this).call(this, this.tagName);
      node.setAttribute('href', value);
      node.setAttribute('target', '_blank');
      return node;
    }
  }, {
    key: 'formats',
    value: function formats(domNode) {
      return domNode.getAttribute('href');
    }
  }, {
    key: 'handleMouseover',
    value: function handleMouseover(evt) {
      if (this.tooltip == null) return;
      var preview = this.tooltip.root.querySelector('a.ql-preview');
      preview.textContent = evt.target.getAttribute('href');
    }
  }, {
    key: 'handleMouseout',
    value: function handleMouseout(evt) {
      if (this.tooltip == null) return;
      var preview = this.tooltip.root.querySelector('a.ql-preview');
      preview.textContent = '';
    }
  }]);
  return Link;
}(Inline);
Link.blotName = 'link';
Link.tagName = 'A';
var Script = function (_Inline) {
  _inherits(Script, _Inline);
  function Script() {
    _classCallCheck(this, Script);
    return _possibleConstructorReturn(this, (Script.__proto__ || Object.getPrototypeOf(Script)).apply(this, arguments));
  }
  _createClass(Script, null, [{
    key: 'create',
    value: function create$$1(value) {
      if (value === 'super') {
        return _get(Script.__proto__ || Object.getPrototypeOf(Script), 'create', this).call(this, 'SUP');
      } else if (value === 'sub') {
        return _get(Script.__proto__ || Object.getPrototypeOf(Script), 'create', this).call(this, 'SUB');
      } else {
        return _get(Script.__proto__ || Object.getPrototypeOf(Script), 'create', this).call(this, value);
      }
    }
  }, {
    key: 'formats',
    value: function formats(domNode) {
      if (domNode.tagName === 'SUB') return 'sub';
      if (domNode.tagName === 'SUP') return 'super';
      return undefined;
    }
  }]);
  return Script;
}(Inline);
Script.blotName = 'script';
Script.tagName = ['SUB', 'SUP'];
var Strike = function (_Inline) {
  _inherits(Strike, _Inline);
  function Strike() {
    _classCallCheck(this, Strike);
    return _possibleConstructorReturn(this, (Strike.__proto__ || Object.getPrototypeOf(Strike)).apply(this, arguments));
  }
  _createClass(Strike, null, [{
    key: 'create',
    value: function create$$1() {
      return _get(Strike.__proto__ || Object.getPrototypeOf(Strike), 'create', this).call(this, this.tagName);
    }
  }]);
  return Strike;
}(Inline);
Strike.blotName = 'strike';
Strike.tagName = 'S';
var Underline = function (_Inline) {
  _inherits(Underline, _Inline);
  function Underline() {
    _classCallCheck(this, Underline);
    return _possibleConstructorReturn(this, (Underline.__proto__ || Object.getPrototypeOf(Underline)).apply(this, arguments));
  }
  _createClass(Underline, null, [{
    key: 'create',
    value: function create$$1() {
      return _get(Underline.__proto__ || Object.getPrototypeOf(Underline), 'create', this).call(this, this.tagName);
    }
  }]);
  return Underline;
}(Inline);
Underline.blotName = 'underline';
Underline.tagName = 'U';
var Blockquote = function (_Block) {
  _inherits(Blockquote, _Block);
  function Blockquote() {
    _classCallCheck(this, Blockquote);
    return _possibleConstructorReturn(this, (Blockquote.__proto__ || Object.getPrototypeOf(Blockquote)).apply(this, arguments));
  }
  return Blockquote;
}(Block);
Blockquote.blotName = 'blockquote';
Blockquote.tagName = 'BLOCKQUOTE';
var Header = function (_Block) {
  _inherits(Header, _Block);
  function Header() {
    _classCallCheck(this, Header);
    return _possibleConstructorReturn(this, (Header.__proto__ || Object.getPrototypeOf(Header)).apply(this, arguments));
  }
  _createClass(Header, null, [{
    key: 'create',
    value: function create$$1(value) {
      return _get(Header.__proto__ || Object.getPrototypeOf(Header), 'create', this).call(this, 'H' + value);
    }
  }, {
    key: 'formats',
    value: function formats(domNode) {
      return domNode.tagName.slice(1);
    }
  }]);
  return Header;
}(Block);
Header.blotName = 'header';
Header.tagName = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'];
var Indent = new ClassAttributor('indent', 'ql-indent-', {
  scope: Scope.BLOCK_ATTRIBUTE,
  whitelist: [1, 2, 3, 4, 5, 6, 7, 8, 9]
});
Indent.add = function (node, value) {
  if (value === 0) {
    this.remove(node);
  } else {
    _get(Indent.__proto__ || Object.getPrototypeOf(Indent), 'add', this).call(this, node, value);
  }
};
var List = function (_Block) {
  _inherits(List, _Block);
  function List() {
    _classCallCheck(this, List);
    return _possibleConstructorReturn(this, (List.__proto__ || Object.getPrototypeOf(List)).apply(this, arguments));
  }
  _createClass(List, null, [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(List.__proto__ || Object.getPrototypeOf(List), 'create', this).call(this, this.tagName);
      if (value === 'checked' || value === 'unchecked') {
        node.setAttribute('data-checked', value === 'checked');
      }
      return node;
    }
  }, {
    key: 'formats',
    value: function formats(domNode) {
      if (domNode.hasAttribute('data-checked')) {
        return domNode.getAttribute('data-checked') === 'true' ? 'checked' : 'unchecked';
      }
      return undefined;
    }
  }]);
  return List;
}(Block);
List.blotName = 'list';
List.tagName = 'LI';
var CodeBlock = function (_Block) {
  _inherits(CodeBlock, _Block);
  function CodeBlock() {
    _classCallCheck(this, CodeBlock);
    return _possibleConstructorReturn(this, (CodeBlock.__proto__ || Object.getPrototypeOf(CodeBlock)).apply(this, arguments));
  }
  _createClass(CodeBlock, [{
    key: 'deleteAt',
    value: function deleteAt$$1(index, length) {
      var _children$find3 = this.children.find(index + length);
      var endBlot = _children$find3.node;
      var endOffset = _children$find3.offset;
      _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'deleteAt', this).call(this, index, length);
      if (endBlot != null && endBlot.next == null && endOffset > 0) {
        this.appendChild(Registry.create('text', '\n'));
      }
    }
  }, {
    key: 'formatAt',
    value: function formatAt$$1(index, length, name, value) {
      if (index + length === this.length()) {
        _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'formatAt', this).call(this, index, length - 1, name, value);
      } else {
        _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'formatAt', this).call(this, index, length, name, value);
      }
    }
  }, {
    key: 'insertAt',
    value: function insertAt$$1(index, value, def) {
      if (index >= this.length() - 1) {
        // Exclude newline
        _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'insertAt', this).call(this, index, value, def);
      } else {
        var parts = value.split('\n');
        if (parts.length > 1) {
          _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'insertAt', this).call(this, index, parts[0], def);
          var after = this.split(index + parts[0].length);
          parts.slice(1).forEach(function (part) {
            var blot = Registry.create(CodeBlock.blotName);
            blot.insertAt(0, part);
            after.parent.insertBefore(blot, after);
          });
        } else {
          _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'insertAt', this).call(this, index, value, def);
        }
      }
    }
  }, {
    key: 'length',
    value: function length$$1() {
      return _get(CodeBlock.prototype.__proto__ || Object.getPrototypeOf(CodeBlock.prototype), 'length', this).call(this);
    }
  }], [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(CodeBlock.__proto__ || Object.getPrototypeOf(CodeBlock), 'create', this).call(this, this.tagName);
      node.setAttribute('spellcheck', false);
      return node;
    }
  }]);
  return CodeBlock;
}(Block);
CodeBlock.blotName = 'code-block';
CodeBlock.tagName = 'PRE';
var BlockContainer = function (_ContainerBlot) {
  _inherits(BlockContainer, _ContainerBlot);
  function BlockContainer() {
    _classCallCheck(this, BlockContainer);
    return _possibleConstructorReturn(this, (BlockContainer.__proto__ || Object.getPrototypeOf(BlockContainer)).apply(this, arguments));
  }
  return BlockContainer;
}(ContainerBlot);
BlockContainer.blotName = 'container';
BlockContainer.scope = Scope.BLOCK_BLOT;
BlockContainer.tagName = 'DIV';
BlockContainer.defaultChild = 'block';
BlockContainer.allowedChildren = [Block];
var Video = function (_EmbedBlot) {
  _inherits(Video, _EmbedBlot);
  function Video() {
    _classCallCheck(this, Video);
    return _possibleConstructorReturn(this, (Video.__proto__ || Object.getPrototypeOf(Video)).apply(this, arguments));
  }
  _createClass(Video, null, [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(Video.__proto__ || Object.getPrototypeOf(Video), 'create', this).call(this, this.tagName);
      node.setAttribute('frameborder', '0');
      node.setAttribute('allowfullscreen', true);
      node.setAttribute('src', value);
      return node;
    }
  }, {
    key: 'value',
    value: function value(domNode) {
      return domNode.getAttribute('src');
    }
  }]);
  return Video;
}(EmbedBlot);
Video.blotName = 'video';
Video.tagName = 'IFRAME';
var Formula = function (_EmbedBlot) {
  _inherits(Formula, _EmbedBlot);
  function Formula() {
    _classCallCheck(this, Formula);
    return _possibleConstructorReturn(this, (Formula.__proto__ || Object.getPrototypeOf(Formula)).apply(this, arguments));
  }
  _createClass(Formula, null, [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(Formula.__proto__ || Object.getPrototypeOf(Formula), 'create', this).call(this, this.tagName);
      node.setAttribute('data-value', value);
      if (window.katex != null) {
        window.katex.render(value, node);
      }
      return node;
    }
  }, {
    key: 'value',
    value: function value(domNode) {
      return domNode.getAttribute('data-value');
    }
  }]);
  return Formula;
}(EmbedBlot);
Formula.blotName = 'formula';
Formula.tagName = 'SPAN';
var Image$1 = function (_EmbedBlot) {
  _inherits(Image$1, _EmbedBlot);
  function Image$$1() {
    _classCallCheck(this, Image$$1);
    return _possibleConstructorReturn(this, (Image$$1.__proto__ || Object.getPrototypeOf(Image$$1)).apply(this, arguments));
  }
  _createClass(Image$$1, null, [{
    key: 'create',
    value: function create$$1(value) {
      var node = _get(Image$$1.__proto__ || Object.getPrototypeOf(Image$$1), 'create', this).call(this, this.tagName);
      node.setAttribute('src', value);
      return node;
    }
  }, {
    key: 'value',
    value: function value(domNode) {
      return domNode.getAttribute('src');
    }
  }]);
  return Image$1;
}(EmbedBlot);
Image$1.blotName = 'image';
Image$1.tagName = 'IMG';
Registry.register(Align, Background, Color, Direction, Font, Size);
Registry.register(Blockquote, Header, Indent, List, CodeBlock, BlockContainer);
Registry.register(Bold, Italic, Link, Script, Strike, Underline);
Registry.register(Formula, Image$1, Video);
*/
// END OF BLOCK TO DELETE

var getCookie = function getCookie(name) {
  var value = '; ' + document.cookie;
  var parts = value.split('; ' + name + '=');
  if (parts.length === 2) return parts.pop().split(';').shift();
};

var CSRF_TOKEN = getCookie('csrftoken');

var XHR = typeof XMLHttpRequest === 'undefined' ? require('xmlhttprequest').XMLHttpRequest : XMLHttpRequest;

var ImageUploader = function () {
  function ImageUploader(quill, options) {
    _classCallCheck(this, ImageUploader);

    this.quill = quill;
    this.options = options;
    this.range = null;

    if (typeof this.options.upload !== 'function') {
      console.warn('[Missing config] upload function that returns a promise is required');
    }

    this.quill.getModule('toolbar').addHandler('image', this.selectLocalImage.bind(this));

    this.handleDrop = this.handleDrop.bind(this);
    this.handlePaste = this.handlePaste.bind(this);

    this.quill.root.addEventListener('drop', this.handleDrop, false);
    this.quill.root.addEventListener('paste', this.handlePaste, false);
  }

  _createClass(ImageUploader, [{
    key: 'selectLocalImage',
    value: function selectLocalImage() {
      this.range = this.quill.getSelection();
      this.fileHolder = document.createElement('input');
      this.fileHolder.setAttribute('type', 'file');
      this.fileHolder.setAttribute('accept', 'image/*');
      this.fileHolder.setAttribute('style', 'visibility:hidden');

      this.fileHolder.onchange = this.fileChanged.bind(this);

      document.body.appendChild(this.fileHolder);

      this.fileHolder.click();

      window.requestAnimationFrame(function () {
        document.body.removeChild(this.fileHolder);
      }.bind(this));
    }
  }, {
    key: 'handleDrop',
    value: function handleDrop(evt) {
      evt.preventDefault();
      var range = this.quill.getSelection();
      var files = evt.dataTransfer.files;

      if (evt.dataTransfer && evt.dataTransfer.files && evt.dataTransfer.files.length) {
        if (document.caretRangeFromPoint) {
          var selection = document.getSelection();
          var _range = document.caretRangeFromPoint(evt.clientX, evt.clientY);
          if (selection && _range) {
            selection.setBaseAndExtent(selection.anchorNode, selection.anchorOffset, _range.startContainer, _range.startOffset);
          }
        } else {
          var _range2 = document.caretPositionFromPoint(evt.clientX, evt.clientY);
          var _selection = document.getSelection();
          _selection.setBaseAndExtent(_range2.offsetNode, _range2.offset, _range2.offsetNode, _range2.offset);
        }

        this.range = this.quill.getSelection();
        this.readFiles(files, this.insertImage.bind(this));
      }
    }
  }, {
    key: 'handlePaste',
    value: function handlePaste(evt) {
      var _this36 = this;

      var range = this.quill.getSelection();
      var files = evt.clipboardData.files;

      if (evt.clipboardData && evt.clipboardData.files && evt.clipboardData.files.length) {
        evt.preventDefault();
        this.range = range;
        this.readFiles(files, function (dataUrl) {
          setTimeout(function () {
            _this36.range = _this36.quill.getSelection();
            _this36.insertImage(dataUrl);
          }, 0);
        });
      }
    }
  }, {
    key: 'fileChanged',
    value: function fileChanged() {
      var file = this.fileHolder.files[0];
      this.readFiles([file], this.insertImage.bind(this));
    }
  }, {
    key: 'readFiles',
    value: function readFiles(files, callback) {
      // Today, only handle one file upload.
      var file = files[0];
      var reader = new FileReader();
      reader.onload = function (e) {
        callback(e.target.result);
      };
      reader.readAsDataURL(file);
    }
  }, {
    key: 'insertImage',
    value: function insertImage(dataUrl) {
      var _this37 = this;

      this.options.upload(dataUrl).then(function (imageUrl) {
        var index = (_this37.range.index + _this37.range.length) / 2;
        _this37.quill.insertEmbed(index, 'image', imageUrl);
      }, function (error) {
        console.warn(error);
      });
    }
  }]);

  return ImageUploader;
}();

Registry.register('modules/imageUploader', ImageUploader);

var BETTER_MAC_ENTER = {
  key: 13,
  shiftKey: true,
  shortKey: true,
  handler: function handler(range) {
    var _this38 = this;

    var currentLeaf = this.quill.getLeaf(range.index)[0];
    if (currentLeaf) {
      (function () {
        var next = currentLeaf.next;

        while (next != null && !(next instanceof BreakBlot)) {
          next = next.next;
        }
        if (next) {
          (function () {
            var offset = next.offset(_this38.quill.scroll);
            _this38.quill.updateContents(new Delta().retain(offset)['delete'](1), 'user');
          })();
        }
      })();
    }
    this.quill.insertText(range.index, '\n', 'user');
    return false; // Do not propagate
  }
};

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var DEFAULT_CONFIG = {
  container: null,
  modules: {
    clipboard: {
      matchers: [
      // Breakline
      [Node.TEXT_NODE, function (node, delta) {
        var text = node.data;
        if (text.indexOf('\n') === -1) return delta;
        var ops = [];
        text.split('\n').forEach(function (part, index) {
          if (index !== 0) ops.push({ insert: '\n' });
          if (part.length > 0) {
            ops.push({ insert: part });
          }
        });
        return new Delta(ops);
      }], [Node.ELEMENT_NODE, function (node, delta) {
        if (node.tagName === 'BR') {
          return new Delta().insert('\n');
        }
        return delta;
      }], [Node.ELEMENT_NODE, function (node, delta) {
        return delta.reduce(function (newDelta, op) {
          if (op.insert && typeof op.insert === 'string' && op.insert.indexOf('\n') === -1) {
            return newDelta.insert(op.insert, op.attributes);
          }
          return newDelta;
        }, new Delta());
      }]]
    },
    keyboard: {
      bindings: {
        'list autofill': {
          key: ' ',
          collapsed: true,
          format: { list: false },
          prefix: /^(1\.|-)$/,
          handler: function handler(range, context) {
            var _quill$getLine = this.quill.getLine(range.index);

            var line = _quill$getLine[0];
            var offset = _quill$getLine[1];

            var value = context.prefix === '1.' ? 'ordered' : 'bullet';
            this.quill.formatLine(range.index, 1, 'list', value, 'user');
            this.quill.deleteText(range.index - offset, context.prefix.length + 1);
          }
        },
        'tab': {
          key: 9,
          handler: function handler(range) {
            if (!range.collapsed) {
              this.quill.formatLine(range.index, range.length, 'indent', '+1');
            } else {
              var _quill$getLine2 = this.quill.getLine(range.index);

              var line = _quill$getLine2[0];
              var offset = _quill$getLine2[1];

              var value = line.formats()['indent'];
              if (value) {
                this.quill.formatLine(range.index, 1, 'indent', '+1');
              } else {
                this.quill.insertText(range.index, Block.TAB, 'user');
              }
            }
          }
        },
        'shift tab': {
          key: 9,
          shiftKey: true,
          handler: function handler(range) {
            if (!range.collapsed) {
              this.quill.formatLine(range.index, range.length, 'indent', '-1');
            } else {
              var _quill$getLine3 = this.quill.getLine(range.index);

              var line = _quill$getLine3[0];
              var offset = _quill$getLine3[1];

              var value = line.formats()['indent'];
              if (value) {
                this.quill.formatLine(range.index, 1, 'indent', '-1');
              }
            }
          }
        },
        'better mac enter': BETTER_MAC_ENTER
      }
    }
  },
  theme: 'default'
};
var THEMES = {
  'default': {
    modules: {
      toolbar: true
    }
  },
  'snow': {
    modules: {
      toolbar: {
        container: [['bold', 'italic', 'underline', 'strike'], [{ 'header': 1 }, { 'header': 2 }], [{ 'list': 'ordered' }, { 'list': 'bullet' }], ['link', 'image']]
      }
    }
  }
};

function expandConfig(config) {
  if (config.theme != null && THEMES[config.theme] != null) {
    config = deepMerge(THEMES[config.theme], config);
  }
  if (config.modules != null && config.modules.toolbar != null && config.modules.toolbar.container == null) {
    config.modules.toolbar.container = [['bold', 'italic', 'underline', 'strike'], [{ 'header': 1 }, { 'header': 2 }], [{ 'list': 'ordered' }, { 'list': 'bullet' }], ['link', 'image']];
  }
  return config;
}

function deepMerge(target, src) {
  if ((typeof target === 'undefined' ? 'undefined' : _typeof(target)) !== 'object' || (typeof src === 'undefined' ? 'undefined' : _typeof(src)) !== 'object') return src;
  Object.keys(src).forEach(function (key) {
    if (src[key] == null) {
      delete target[key];
    } else if (target[key] == null) {
      target[key] = src[key];
    } else if (Array.isArray(target[key]) && Array.isArray(src[key])) {
      target[key] = src[key];
    } else {
      target[key] = deepMerge(target[key], src[key]);
    }
  });
  return target;
}

var Emitter = function () {
  function Emitter() {
    _classCallCheck(this, Emitter);

    this.listeners = {};
  }

  _createClass(Emitter, [{
    key: 'emit',
    value: function emit() {
      for (var _len = arguments.length, args = Array(_len), _key = 0; _key < _len; _key++) {
        args[_key] = arguments[_key];
      }

      var event = args[0];
      if (this.listeners[event] == null) return;
      this.listeners[event].forEach(function (listener) {
        listener.apply(undefined, args.slice(1));
      });
    }
  }, {
    key: 'listen',
    value: function listen(event, listener) {
      // TODO use WeakMap
      this.listeners[event] = this.listeners[event] || [];
      this.listeners[event].push(listener);
    }
  }]);

  return Emitter;
}();

Emitter.events = {
  EDITOR_CHANGE: 'editor-change',
  SELECTION_CHANGE: 'selection-change',
  TEXT_CHANGE: 'text-change'
};
Emitter.sources = {
  API: 'api',
  SILENT: 'silent',
  USER: 'user'
};

var Selection = function () {
  function Selection(root) {
    var _this39 = this;

    _classCallCheck(this, Selection);

    this.root = root;
    this.emitter = new Emitter();
    this.range = null;
    ['blur', 'focus'].forEach(function (eventName) {
      _this39.root.addEventListener(eventName, function () {
        _this39.update(Emitter.sources.USER);
      });
    });
    this.root.addEventListener('keyup', function () {
      _this39.update(Emitter.sources.USER);
    });
    this.root.addEventListener('mousedown', function () {
      setTimeout(function () {
        _this39.update(Emitter.sources.USER);
      }, 0);
    });
    this.update(Emitter.sources.SILENT); // Must be after listeners
  }

  _createClass(Selection, [{
    key: 'checkFocus',
    value: function checkFocus() {
      return document.activeElement === this.root;
    }
  }, {
    key: 'focus',
    value: function focus() {
      if (this.checkFocus()) return;
      this.root.focus();
    }
  }, {
    key: 'format',
    value: function format$$1(name, value) {
      if (this.range == null) return;
      this.emitter.emit(Emitter.events.TEXT_CHANGE, new Delta().retain(this.range.index).retain(this.range.length, _defineProperty({}, name, value)), Emitter.sources.USER);
      this.update(Emitter.sources.USER);
    }
  }, {
    key: 'getRange',
    value: function getRange() {
      if (!this.checkFocus()) return [null, null, null, null];
      var selection = window.getSelection();
      if (selection.rangeCount === 0) return [null, null, null, null];
      var range = selection.getRangeAt(0);
      var startLeaf = Registry.find(range.startContainer, true);
      var endLeaf = Registry.find(range.endContainer, true);
      if (startLeaf == null || endLeaf == null) return [null, null, null, null];
      var startIndex = startLeaf.offset(this.root.blot);
      var startOffset = startLeaf.index(range.startContainer, range.startOffset);
      var endIndex = endLeaf.offset(this.root.blot);
      var endOffset = endLeaf.index(range.endContainer, range.endOffset);
      var start = startIndex + startOffset;
      var end = endIndex + endOffset;
      return [start, end, startLeaf, endLeaf];
    }
  }, {
    key: 'setRange',
    value: function setRange(index) {
      var length = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 0;
      var source = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : Emitter.sources.API;

      if (!this.checkFocus()) this.focus();
      var selection = window.getSelection();
      if (selection.rangeCount > 0) selection.removeAllRanges();
      if (index === null) return;
      var range = document.createRange();
      var startNode = this.root.blot.at(index);
      var startOffset = index - startNode.offset(this.root.blot);
      range.setStart(startNode.domNode, startOffset);
      var endNode = this.root.blot.at(index + length);
      var endOffset = index + length - endNode.offset(this.root.blot);
      range.setEnd(endNode.domNode, endOffset);
      selection.addRange(range);
      this.update(source);
    }
  }, {
    key: 'update',
    value: function update() {
      var source = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : Emitter.sources.SILENT;

      var _getRange = this.getRange(),
          start = _getRange[0],
          end = _getRange[1],
          startLeaf = _getRange[2],
          endLeaf = _getRange[3];

      var oldRange = this.range;
      if (start !== null) {
        this.range = { index: start, length: end - start };
      } else {
        this.range = null;
      }
      if (oldRange !== this.range) {
        this.emitter.emit(Emitter.events.SELECTION_CHANGE, this.range, source);
      }
    }
  }]);

  return Selection;
}();

var _extends$1 = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var formats$1 = {
  'align': Align,
  'background': Background,
  'blockquote': Blockquote,
  'bold': Bold,
  'code-block': CodeBlock,
  'color': Color,
  'direction': Direction,
  'font': Font,
  'formula': Formula,
  'header': Header,
  'image': Image$1,
  'indent': Indent,
  'italic': Italic,
  'link': Link,
  'list': List,
  'script': Script,
  'size': Size,
  'strike': Strike,
  'underline': Underline,
  'video': Video
};

var Quill = function () {
  function Quill(container) {
    var config = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};

    _classCallCheck(this, Quill);

    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    if (this.container == null) {
      return console.error('Invalid Quill container', container);
    }
    this.id = 'quill-container-' + Math.random().toString(36).slice(2);
    this.container.classList.add(this.id);
    this.container.innerHTML = '<div class="ql-editor" contenteditable="true"></div><div class="ql-clipboard" contenteditable="true" tabindex="-1"></div>';
    this.root = this.container.querySelector('.ql-editor');
    this.clipboard = this.container.querySelector('.ql-clipboard');
    this.config = expandConfig(_extends$1({}, DEFAULT_CONFIG, config));
    this.emitter = new Emitter();
    this.scroll = Registry.create(this.root);
    this.selection = new Selection(this.root);
    this.theme = new this.config.theme(this, this.config); // eslint-disable-line new-cap
    this.keyboard = this.theme.addModule('keyboard');
    this.clipboard = this.theme.addModule('clipboard');
    this.history = this.theme.addModule('history');
    this.editor = new Editor(this.scroll, this.emitter);
    this.selection.emitter.listen(Emitter.events.SELECTION_CHANGE, function (range, source) {
      if (range == null) return;
      var formats = this.getFormat(range);
      this.emitter.emit(Emitter.events.SELECTION_CHANGE, range, formats, source);
    }.bind(this));
    this.emitter.listen(Emitter.events.EDITOR_CHANGE, function (type, delta, source) {
      if (type === Emitter.events.TEXT_CHANGE) {
        this.selection.update(source);
      }
      this.emitter.emit(Emitter.events.TEXT_CHANGE, delta, source);
    }.bind(this));
  }

  _createClass(Quill, [{
    key: 'deleteText',
    value: function deleteText(index, length, source) {
      source = source || Emitter.sources.API;
      var change = this.editor.delete(index, length);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'disable',
    value: function disable() {
      this.enable(false);
    }
  }, {
    key: 'enable',
    value: function enable() {
      var value = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : true;

      this.root.setAttribute('contenteditable', value);
      this.container.classList.toggle('ql-disabled', !value);
    }
  }, {
    key: 'format',
    value: function format(name, value) {
      var source = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : Emitter.sources.API;

      var range = this.getSelection(true);
      var change = new Delta();
      if (range == null) {} else if (Registry.query(name, Scope.BLOT)) {
        change.retain(range.index).retain(range.length, _defineProperty({}, name, value));
      } else if (range.length > 0) {
        change.retain(range.index).retain(range.length, _defineProperty({}, name, value));
      } else {
        this.selection.format(name, value);
      }
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'formatLine',
    value: function formatLine(index, length) {
      var name = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
      var value = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : null;

      var source = Emitter.sources.API;
      if (typeof name === 'string') {
        name = _defineProperty({}, name, value);
        source = value;
      } else {
        source = name;
      }
      var change = this.editor.formatLine(index, length, name);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'formatText',
    value: function formatText(index, length) {
      var name = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
      var value = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : null;

      var source = Emitter.sources.API;
      if (typeof name === 'string') {
        name = _defineProperty({}, name, value);
        source = value;
      } else {
        source = name;
      }
      var change = this.editor.formatText(index, length, name);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'getContents',
    value: function getContents(index, length) {
      index = index || 0;
      length = length || this.getLength() - index;
      return this.editor.getContents(index, length);
    }
  }, {
    key: 'getFormat',
    value: function getFormat() {
      var index = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : this.getSelection(true);
      var length = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 0;

      if (typeof index === 'number') {
        return this.editor.getFormat(index, length);
      } else {
        return this.editor.getFormat(index.index, index.length);
      }
    }
  }, {
    key: 'getLength',
    value: function getLength() {
      return this.scroll.length();
    }
  }, {
    key: 'getLeaf',
    value: function getLeaf(index) {
      return this.scroll.find(index, true);
    }
  }, {
    key: 'getLine',
    value: function getLine(index) {
      return this.scroll.find(index);
    }
  }, {
    key: 'getModule',
    value: function getModule(name) {
      return this.theme.modules[name];
    }
  }, {
    key: 'getSelection',
    value: function getSelection() {
      var focus = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;

      if (focus) this.selection.focus();
      this.selection.update();
      return this.selection.range;
    }
  }, {
    key: 'getText',
    value: function getText(index, length) {
      index = index || 0;
      length = length || this.getLength() - index;
      return this.editor.getText(index, length);
    }
  }, {
    key: 'insertEmbed',
    value: function insertEmbed(index, type, value, source) {
      source = source || Emitter.sources.API;
      var change = this.editor.insertEmbed(index, type, value);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'insertText',
    value: function insertText(index, text, name, value, source) {
      var formats = {};
      if (typeof name === 'string') {
        formats[name] = value;
        source = source || Emitter.sources.API;
      } else {
        formats = name;
        source = value || Emitter.sources.API;
      }
      var change = this.editor.insertText(index, text, formats);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'isEnabled',
    value: function isEnabled() {
      return this.root.getAttribute('contenteditable') === 'true';
    }
  }, {
    key: 'on',
    value: function on(event, listener) {
      this.emitter.listen(event, listener);
    }
  }, {
    key: 'pasteHTML',
    value: function pasteHTML(index, html, source) {
      this.clipboard.dangerouslyPasteHTML(index, html, source);
    }
  }, {
    key: 'removeFormat',
    value: function removeFormat(index, length, source) {
      var formats = this.getFormat(index, length);
      var change = new Delta().retain(index);
      Object.keys(formats).forEach(function (name) {
        change.retain(length, _defineProperty({}, name, false)); // TODO: Fix this API
      });
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
    }
  }, {
    key: 'setContents',
    value: function setContents(delta) {
      var source = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : Emitter.sources.API;

      if (Array.isArray(delta)) {
        delta = new Delta(delta);
      }
      var change = new Delta().delete(this.getLength()).concat(delta);
      this.editor.applyDelta(change);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'setSelection',
    value: function setSelection(index, length, source) {
      if (typeof index === 'number') {
        this.selection.setRange(index, length, source);
      } else {
        source = length || Emitter.sources.API;
        this.selection.setRange(index.index, index.length, source);
      }
    }
  }, {
    key: 'setText',
    value: function setText(text) {
      var source = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : Emitter.sources.API;

      var delta = new Delta().insert(text);
      return this.setContents(delta, source);
    }
  }, {
    key: 'updateContents',
    value: function updateContents(delta) {
      var source = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : Emitter.sources.API;

      if (Array.isArray(delta)) {
        delta = new Delta(delta);
      }
      this.editor.applyDelta(delta);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, delta, source);
      return delta;
    }
  }], [{
    key: 'find',
    value: function find$$1(node) {
      var bubble = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

      return Registry.find(node, bubble);
    }
  }, {
    key: 'register',
    value: function register$$1(name, target, overwrite) {
      if (typeof name !== 'string') {
        var results = [];
        for (var key in name) {
          results.push(this.register(key, name[key], target));
        }
        return results;
      }
      return Registry.register(target);
    }
  }]);

  return Quill;
}();

Quill.DEFAULTS = DEFAULT_CONFIG;
Quill.events = Emitter.events;
Quill.sources = Emitter.sources;
Quill.version = global.QUILL_VERSION || '1.3.6';

Quill.imports = {
  'delta': Delta,
  'parchment': Parchment,
  'core/editor': Editor,
  'core/emitter': Emitter,
  'core/selection': Selection,
  'core/quill': Quill,

  'blots/block': Block,
  'blots/container': BlockContainer,
  'blots/inline': Inline,
  'blots/scroll': Scroll,
  'blots/text': TextBlot,

  'formats/align': Align,
  'formats/background': Background,
  'formats/blockquote': Blockquote,
  'formats/bold': Bold,
  'formats/code': CodeBlock,
  'formats/color': Color,
  'formats/direction': Direction,
  'formats/font': Font,
  'formats/formula': Formula,
  'formats/header': Header,
  'formats/image': Image$1,
  'formats/indent': Indent,
  'formats/italic': Italic,
  'formats/link': Link,
  'formats/list': List,
  'formats/script': Script,
  'formats/size': Size,
  'formats/strike': Strike,
  'formats/underline': Underline,
  'formats/video': Video,

  'modules/clipboard': Clipboard,
  'modules/history': History,
  'modules/keyboard': Keyboard,
  'modules/syntax': Syntax,
  'modules/toolbar': Toolbar, // Fixed 'moduless' typo
  'modules/uploader': ImageUploader,

  'themes/default': Theme,
  'themes/snow': SnowTheme
};

var _extends$2 = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var DEFAULTS = {
  modules: {
    toolbar: {
      container: [['bold', 'italic', 'underline', 'strike'], [{ 'header': 1 }, { 'header': 2 }], [{ 'list': 'ordered' }, { 'list': 'bullet' }], ['clean']]
    }
  },
  theme: 'default'
};

var expandConfig$1 = function expandConfig(config) {
  if (config.theme != null && config.theme !== 'default') {
    config = deepMerge$1(THEMES[config.theme], config);
  }
  if (config.modules != null && config.modules.toolbar != null && config.modules.toolbar.container == null) {
    config.modules.toolbar.container = DEFAULTS.modules.toolbar.container;
  }
  return config;
};

var deepMerge$1 = function deepMerge(target, src) {
  if ((typeof target === 'undefined' ? 'undefined' : _typeof(target)) !== 'object' || (typeof src === 'undefined' ? 'undefined' : _typeof(src)) !== 'object') return src;
  Object.keys(src).forEach(function (key) {
    if (src[key] == null) {
      delete target[key];
    } else if (target[key] == null) {
      target[key] = src[key];
    } else if (Array.isArray(target[key]) && Array.isArray(src[key])) {
      target[key] = src[key];
    } else {
      target[key] = deepMerge(target[key], src[key]);
    }
  });
  return target;
};

var Quill$1 = function () {
  function Quill(container) {
    var config = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};

    _classCallCheck(this, Quill);

    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    if (this.container == null) {
      return console.error('Invalid Quill container', container);
    }
    this.container.classList.add('ql-container');
    this.container.innerHTML = '<div class="ql-editor" contenteditable="true"></div>';
    this.root = this.container.querySelector('.ql-editor');
    this.config = expandConfig$1(_extends$2({}, DEFAULTS, config));
    this.emitter = new Emitter();
    this.scroll = Registry.create(this.root);
    this.selection = new Selection(this.root);
    this.theme = new this.config.theme(this, this.config); // eslint-disable-line new-cap
    this.keyboard = this.theme.addModule('keyboard');
    this.clipboard = this.theme.addModule('clipboard');
    this.history = this.theme.addModule('history');
    this.editor = new Editor(this.scroll, this.emitter);
  }

  _createClass(Quill, [{
    key: 'deleteText',
    value: function deleteText(index, length) {
      var source = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : Emitter.sources.API;

      var change = this.editor.delete(index, length);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'disable',
    value: function disable() {
      this.enable(false);
    }
  }, {
    key: 'enable',
    value: function enable() {
      var value = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : true;

      this.root.setAttribute('contenteditable', value);
    }
  }, {
    key: 'format',
    value: function format(name, value) {
      var source = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : Emitter.sources.API;

      var range = this.getSelection(true);
      var change = new Delta();
      if (range == null) {} else if (Registry.query(name, Scope.BLOT)) {
        change.retain(range.index).retain(range.length, _defineProperty({}, name, value));
      } else if (range.length > 0) {
        change.retain(range.index).retain(range.length, _defineProperty({}, name, value));
      }
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
    }
  }, {
    key: 'formatLine',
    value: function formatLine(index, length) {
      var name = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
      var value = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : null;

      var source = Emitter.sources.API;
      if (typeof name === 'string') {
        name = _defineProperty({}, name, value);
        source = value;
      } else {
        source = name;
      }
      var change = this.editor.formatLine(index, length, name);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'formatText',
    value: function formatText(index, length) {
      var name = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : null;
      var value = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : null;

      var source = Emitter.sources.API;
      if (typeof name === 'string') {
        name = _defineProperty({}, name, value);
        source = value;
      } else {
        source = name;
      }
      var change = this.editor.formatText(index, length, name);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'getContents',
    value: function getContents(index, length) {
      index = index || 0;
      length = length || this.getLength() - index;
      return this.editor.getContents(index, length);
    }
  }, {
    key: 'getFormat',
    value: function getFormat(index, length) {
      index = index || this.getSelection(true);
      if (typeof index === 'number') {
        return this.editor.getFormat(index, length);
      } else {
        return this.editor.getFormat(index.index, index.length);
      }
    }
  }, {
    key: 'getLength',
    value: function getLength() {
      return this.scroll.length();
    }
  }, {
    key: 'getModule',
    value: function getModule(name) {
      return this.theme.modules[name];
    }
  }, {
    key: 'getSelection',
    value: function getSelection() {
      var focus = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : false;

      if (focus) this.selection.focus();
      this.selection.update();
      return this.selection.range;
    }
  }, {
    key: 'getText',
    value: function getText(index, length) {
      index = index || 0;
      length = length || this.getLength() - index;
      return this.editor.getText(index, length);
    }
  }, {
    key: 'insertEmbed',
    value: function insertEmbed(index, type, value, source) {
      source = source || Emitter.sources.API;
      var change = this.editor.insertEmbed(index, type, value);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'insertText',
    value: function insertText(index, text, name, value, source) {
      var formats = {};
      if (typeof name === 'string') {
        formats[name] = value;
        source = source || Emitter.sources.API;
      } else {
        formats = name;
        source = value || Emitter.sources.API;
      }
      var change = this.editor.insertText(index, text, formats);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'isEnabled',
    value: function isEnabled() {
      return this.root.getAttribute('contenteditable') === 'true';
    }
  }, {
    key: 'on',
    value: function on(event, listener) {
      this.emitter.listen(event, listener);
    }
  }, {
    key: 'pasteHTML',
    value: function pasteHTML(index, html, source) {
      this.clipboard.pasteHTML(index, html, source);
    }
  }, {
    key: 'removeFormat',
    value: function removeFormat(index, length, source) {
      var formats = this.getFormat(index, length);
      var change = new Delta().retain(index);
      Object.keys(formats).forEach(function (name) {
        change.retain(length, _defineProperty({}, name, false)); // TODO: Fix this API
      });
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
    }
  }, {
    key: 'setContents',
    value: function setContents(delta) {
      var source = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : Emitter.sources.API;

      if (Array.isArray(delta)) {
        delta = new Delta(delta);
      }
      var change = new Delta().delete(this.getLength()).concat(delta);
      this.editor.applyDelta(change);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, change, source);
      return change;
    }
  }, {
    key: 'setSelection',
    value: function setSelection(index, length, source) {
      if (typeof index === 'number') {
        this.selection.setRange(index, length, source);
      } else {
        source = length || Emitter.sources.API;
        this.selection.setRange(index.index, index.length, source);
      }
    }
  }, {
    key: 'setText',
    value: function setText(text) {
      var source = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : Emitter.sources.API;

      var delta = new Delta().insert(text);
      return this.setContents(delta, source);
    }
  }, {
    key: 'updateContents',
    value: function updateContents(delta) {
      var source = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : Emitter.sources.API;

      if (Array.isArray(delta)) {
        delta = new Delta(delta);
      }
      this.editor.applyDelta(delta);
      this.emitter.emit(Emitter.events.EDITOR_CHANGE, Emitter.events.TEXT_CHANGE, delta, source);
      return delta;
    }
  }], [{
    key: 'find',
    value: function find$$1(node) {
      var bubble = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : false;

      return Registry.find(node, bubble);
    }
  }, {
    key: 'register',
    value: function register$$1(name, target, overwrite) {
      if (typeof name !== 'string') {
        var results = [];
        for (var key in name) {
          results.push(this.register(key, name[key], target));
        }
        return results;
      }
      return Registry.register(target);
    }
  }]);

  return Quill;
}();

Quill$1.DEFAULTS = DEFAULTS;
Quill$1.events = Emitter.events;
Quill$1.sources = Emitter.sources;
Quill$1.version = global.QUILL_VERSION || '1.3.6';

Quill$1.imports = {
  'delta': Delta,
  'parchment': Parchment,
  'core/editor': Editor,
  'core/emitter': Emitter,
  'core/selection': Selection,
  'core/quill': Quill$1,

  'blots/block': Block,
  'blots/inline': Inline,
  'blots/scroll': Scroll,
  'blots/text': TextBlot,

  'formats/align': Align,
  'formats/blockquote': Blockquote,
  'formats/bold': Bold,
  'formats/code': CodeBlock,
  'formats/header': Header,
  'formats/indent': Indent,
  'formats/italic': Italic,
  'formats/link': Link,
  'formats/list': List,
  'formats/script': Script,
  'formats/strike': Strike,
  'formats/underline': Underline,

  'modules/clipboard': Clipboard,
  TwoClick: TwoClick,
  'modules/history': History,
  'modules/keyboard': Keyboard,
  'modules/toolbar': Toolbar,

  'themes/default': Theme
};

var BaseTheme = function () {
  function BaseTheme(quill, options) {
    _classCallCheck(this, BaseTheme);

    this.quill = quill;
    this.options = options;
    this.modules = {};
  }

  _createClass(BaseTheme, [{
    key: 'addModule',
    value: function addModule(name) {
      var module = new Quill.imports['modules/' + name](this.quill, this.options.modules[name] || {}); // Fixed 'n' typo
      this.modules[name] = module;
      return module;
    }
  }]);

  return BaseTheme;
}();

var BaseTooltip = function () {
  function BaseTooltip(quill, options) {
    _classCallCheck(this, BaseTooltip);

    this.quill = quill;
    this.options = options;
    this.root = quill.addContainer('ql-tooltip');
    this.root.innerHTML = this.options.template;
  }

  _createClass(BaseTooltip, [{
    key: 'hide',
    value: function hide() {
      this.root.classList.add('ql-hidden');
    }
  }, {
    key: 'position',
    value: function position(reference) {
      this.root.style.left = reference.left + reference.width / 2 - this.root.offsetWidth / 2 + 'px';
      this.root.style.top = reference.bottom + 10 + 'px';
    }
  }, {
    key: 'show',
    value: function show() {
      this.root.classList.remove('ql-hidden');
    }
  }]);

  return BaseTooltip;
}();

var BubbleTooltip = function (_BaseTooltip) {
  _inherits(BubbleTooltip, _BaseTooltip);

  function BubbleTooltip() {
    _classCallCheck(this, BubbleTooltip);

    return _possibleConstructorReturn(this, (BubbleTooltip.__proto__ || Object.getPrototypeOf(BubbleTooltip)).apply(this, arguments));
  }

  _createClass(BubbleTooltip, [{
    key: 'listen',
    value: function listen() {
      var _this41 = this;

      this.quill.on(Quill.events.SELECTION_CHANGE, function (range, source) {
        if (range == null || range.length === 0 || source === Quill.sources.SILENT) {
          _this41.hide();
        } else {
          var bounds = _this41.quill.getBounds(range);
          _this41.position(bounds);
          _this41.show();
        }
      });
    }
  }]);

  return BubbleTooltip;
}(BaseTooltip);

BubbleTooltip.TEMPLATE = ['<span class="ql-format-button ql-bold">Bold</span>', '<span class="ql-format-button ql-italic">Italic</span>', '<span class="ql-format-button ql-link">Link</span>'].join('');

var SnowTooltip = function (_BaseTooltip) {
  _inherits(SnowTooltip, _BaseTooltip);

  function SnowTooltip() {
    _classCallCheck(this, SnowTooltip);

    return _possibleConstructorReturn(this, (SnowTooltip.__proto__ || Object.getPrototypeOf(SnowTooltip)).apply(this, arguments));
  }

  _createClass(SnowTooltip, [{
    key: 'listen',
    value: function listen() {
      var _this43 = this;

      var input = this.root.querySelector('input[type=text]');
      var preview = this.root.querySelector('a.ql-preview');
      this.quill.on(Quill.events.SELECTION_CHANGE, function (range, source) {
        if (range == null || range.length === 0 || source === Quill.sources.SILENT) {
          return _this43.hide();
        }
        var formats = _this43.quill.getFormat(range);
        if (formats.link) {
          input.value = formats.link;
          preview.textContent = formats.link;
          _this43.root.classList.add('ql-editing'); // Fixed _this44 typo
        } else {
          input.value = 'http://';
          preview.textContent = 'http://';
          _this43.root.classList.remove('ql-editing');
        }
        var bounds = _this43.quill.getBounds(range);
        _this43.position(bounds);
        _this43.show();
      });
      this.root.querySelector('a.ql-action').addEventListener('click', function (event) {
        if (_this43.root.classList.contains('ql-editing')) {
          var value = input.value;
          if (value.indexOf('http://') !== 0 && value.indexOf('https://') !== 0) {
            value = 'http://' + value;
          }
          _this43.quill.format('link', value, Quill.sources.USER);
        }
        var range = _this43.quill.getSelection(true);
        _this43.quill.setSelection(range.index + range.length, 0, Quill.sources.USER);
        _this43.hide();
      });
    }
  }]);

  return SnowTooltip;
}(BaseTooltip);

SnowTooltip.TEMPLATE = ['<a class="ql-preview" target="_blank" href="about:blank"></a>', '<input type="text">', '<a class="ql-action"></a>'].join('');

var SnowTheme = function (_BaseTheme) {
  _inherits(SnowTheme, _BaseTheme);

  function SnowTheme(quill, options) {
    _classCallCheck(this, SnowTheme);

    var _this44 = _possibleConstructorReturn(this, (SnowTheme.__proto__ || Object.getPrototypeOf(SnowTheme)).call(this, quill, options));

    _this44.quill.container.classList.add('ql-snow');
    _this44.tooltip = new SnowTooltip(_this44.quill, options);
    if (_this44.options.modules.toolbar) {
      _this44.modules.toolbar.options.handlers.link = function (value) {
        if (!value) {
          this.quill.format('link', false, Quill.sources.USER);
        }
      };
    }
    return _this44;
  }

  _createClass(SnowTheme, [{
    key: 'extendToolbar',
    value: function extendToolbar(toolbar) {
      if (toolbar.options.container == null) return;
      var container = typeof toolbar.options.container === 'string' ? document.querySelector(toolbar.options.container) : toolbar.options.container;
      container.classList.add('ql-toolbar');
      container.classList.add('ql-snow');
      this.buildButtons(container.querySelectorAll('button'), toolbar);
      this.buildPickers(container.querySelectorAll('span.ql-picker'), toolbar);
      this.tooltip.listen();
    }
  }]);

  return SnowTheme;
}(BaseTheme);

SnowTheme.DEFAULTS = {
  modules: {
    toolbar: {
      handlers: {
        'link': function link(value) {
          if (value) {
            var range = this.quill.getSelection();
            if (range == null || range.length === 0) return;
            var preview = this.quill.getText(range);
            if (/^\S+@\S+\.\S+$/.test(preview)) {
              preview = 'mailto:' + preview;
            }
            var tooltip = this.quill.theme.tooltip;
            tooltip.root.querySelector('input[type=text]').value = preview;
            tooltip.root.classList.add('ql-editing');
            tooltip.position(this.quill.getBounds(range));
            tooltip.show();
          } else {
            this.quill.format('link', false);
          }
        }
      }
    }
  }
};

function Quill$2(container, options) {
  options = options || {};
  options = deepMerge$1(SnowTheme.DEFAULTS, options);
  var quill = new Quill(container, options);
  quill.theme.extendToolbar(quill.modules.toolbar);
  return quill;
}
Quill$2.imports = Quill.imports;

return Quill$2;

})));


