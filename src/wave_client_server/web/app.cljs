;; /app: the logged-in user's Wave client, run in the page by scittle.
;;
;; Three panes after the 2009 client (experiments/014 element map):
;; folders + contacts | wave list | open wave. Every call goes to the same
;; origin's /api/...; the browser resends the Basic credentials it was given
;; for /app, so this file never sees a password.

(ns wave.app
  (:require [clojure.string :as str]
            [replicant.dom :as replicant]))

(def poll-interval-ms 10000)
(def gadget-choices ["yes" "no" "maybe"])
(def wave-actions
  [["read" "Read"] ["unread" "Unread"] ["archive" "Archive"] ["unarchive" "Unarchive"]
   ["mute" "Mute"] ["unmute" "Unmute"] ["spam" "Spam"] ["trash" "Trash"] ["restore" "Restore"]])

(defonce state
  (atom {:me nil
         :avatar-files {}
         :folders []
         :contacts []
         :folder "inbox"
         :query ""
         :waves []
         :open-id nil
         :open-wave nil
         :reply-parent nil
         :reply-text ""
         :wave-reply-text ""
         :tag-text ""
         :participant-text ""
         :new-title ""
         :error nil}))

;; ------------------------------------------------------------------ http

(defn api-url
  "Absolute same-origin URL. location.origin never carries userinfo, so this
  works even when the page was opened as http://user:pass@host/app."
  [path]
  (str (.-origin js/location) path))

(defn encode [text] (js/encodeURIComponent text))

(defn wave-path [wave-id] (str "/api/waves/" (encode wave-id)))

(defn request
  ([method path] (request method path nil))
  ([method path body]
   (let [options (cond-> {:method method
                          :credentials "same-origin"
                          :headers {"Accept" "application/json"}}
                   body (assoc :body (.stringify js/JSON (clj->js body))
                               :headers {"Accept" "application/json"
                                         "Content-Type" "application/json"}))]
     (-> (js/fetch (api-url path) (clj->js options))
         (.then (fn [response]
                  (if (.-ok response)
                    (.json response)
                    (throw (js/Error. (str method " " path " failed: " (.-status response)))))))
         (.then (fn [data] (js->clj data :keywordize-keys true)))))))

(defn show-error! [error]
  (swap! state assoc :error (.-message error)))

(defn clear-error! [] (swap! state assoc :error nil))

;; ------------------------------------------------------------------ loading

(defn load-me! []
  (-> (request "GET" "/api/me")
      (.then #(swap! state assoc :me %))
      (.catch show-error!)))

(defn load-avatars! []
  (-> (js/fetch (api-url "/avatars/manifest.json"))
      (.then #(.json %))
      (.then (fn [manifest]
               (swap! state assoc :avatar-files
                      (js->clj (.-avatars manifest)))))
      (.catch (fn [_] nil))))

(defn load-folders! []
  (-> (request "GET" "/api/folders")
      (.then #(swap! state assoc :folders %))
      (.catch show-error!)))

(defn load-contacts! []
  (-> (request "GET" "/api/contacts")
      (.then #(swap! state assoc :contacts %))
      (.catch show-error!)))

(defn load-list! []
  (let [{:keys [folder query]} @state]
    (-> (request "GET" (str "/api/waves?folder=" (encode folder) "&q=" (encode query)))
        (.then #(swap! state assoc :waves %))
        (.catch show-error!))))

(defn load-open-wave! []
  (if-let [wave-id (:open-id @state)]
    (-> (request "GET" (str (wave-path wave-id) "/view"))
        (.then #(swap! state assoc :open-wave %))
        (.catch show-error!))
    (js/Promise.resolve nil)))

(defn refresh! []
  (load-folders!)
  (load-list!)
  (load-open-wave!))

;; ------------------------------------------------------------------ actions

(defn open-wave!
  "Show the wave as it is (unread blips highlighted), then mark it read and
  refresh the list so its badge clears."
  [wave-id]
  (swap! state assoc :open-id wave-id :open-wave nil :reply-parent nil :reply-text "")
  (-> (load-open-wave!)
      (.then #(request "POST" (str (wave-path wave-id) "/read")))
      (.then (fn [_] (load-folders!) (load-list!)))
      (.catch show-error!)))

(defn wave-action! [action]
  (when-let [wave-id (:open-id @state)]
    (-> (request "POST" (str (wave-path wave-id) "/" action))
        (.then refresh!)
        (.catch show-error!))))

(defn choose-folder! [folder-name]
  (swap! state assoc :folder folder-name)
  (load-list!))

(defn search! [query]
  (swap! state assoc :query query)
  (load-list!))

(defn vote! [gadget-id choice]
  (let [wave-id (:open-id @state)]
    (-> (request "POST" (str (wave-path wave-id) "/gadgets/" (encode gadget-id) "/vote")
                 {:choice choice})
        (.then refresh!)
        (.catch show-error!))))

(defn post-reply! [parent-id text-key]
  (let [wave-id (:open-id @state)
        text (str/trim (get @state text-key))]
    (when (seq text)
      (-> (request "POST" (str (wave-path wave-id) "/blips")
                   (cond-> {:text text} parent-id (assoc :parent parent-id)))
          (.then (fn [_]
                   (swap! state assoc text-key "" :reply-parent nil)
                   (refresh!)))
          (.catch show-error!)))))

(defn change-tags! [change]
  (-> (request "POST" (str (wave-path (:open-id @state)) "/tags") change)
      (.then (fn [_] (swap! state assoc :tag-text "") (refresh!)))
      (.catch show-error!)))

(defn add-participant! []
  (let [address (str/trim (:participant-text @state))]
    (when (seq address)
      (-> (request "POST" (str (wave-path (:open-id @state)) "/participants") {:address address})
          (.then (fn [_] (swap! state assoc :participant-text "") (refresh!)))
          (.catch show-error!)))))

(defn create-wave! []
  (let [title (str/trim (:new-title @state))]
    (when (seq title)
      (-> (request "POST" "/api/waves" {:title title :text title})
          (.then (fn [summary]
                   (swap! state assoc :new-title "")
                   (load-folders!)
                   (load-list!)
                   (open-wave! (:id summary))))
          (.catch show-error!)))))

;; ------------------------------------------------------------------ helpers

(defn avatar-src [address]
  (let [avatar-files (:avatar-files @state)]
    (cond
      (contains? avatar-files address) (str "/avatars/" (get avatar-files address))
      (str/starts-with? address "public@") "/avatars/public.svg"
      :else "/avatars/default.svg")))

(defn local-name [address] (first (str/split (or address "") #"@")))

(defn avatar
  ([address] (avatar address "avatar"))
  ([address class-name]
   [:img {:class class-name :src (avatar-src address) :alt (local-name address) :title address}]))

(defn parse-time [iso-text]
  (when iso-text
    (js/Date. (if (re-find #"(Z|[+-]\d\d:\d\d)$" iso-text) iso-text (str iso-text "Z")))))

(defn short-time [iso-text]
  (when-let [moment (parse-time iso-text)]
    (if (= (.toDateString moment) (.toDateString (js/Date.)))
      (.toLocaleTimeString moment js/undefined #js {:hour "numeric" :minute "2-digit"})
      (.toLocaleDateString moment js/undefined #js {:month "short" :day "numeric"}))))

(defn on-enter [action]
  (fn [event] (when (= "Enter" (.-key event)) (action))))

(defn bind [state-key]
  {:value (get @state state-key)
   :on {:input (fn [event] (swap! state assoc state-key (.. event -target -value)))}})

(defn classes [& names] (vec (remove nil? names)))

;; ------------------------------------------------------------------ views

(defn topbar-view [{:keys [me]}]
  [:header.topbar
   [:h1 "Wave"]
   [:span.spacer]
   (when me
     [:span.me (avatar (:address me)) [:span (:address me)]])])

(defn navigation-view [{:keys [folders folder contacts]}]
  [:nav.pane.nav
   [:h2 "Navigation"]
   [:ul
    (for [{:keys [name total unread]} folders]
      [:li {:replicant/key name
            :class (classes (when (= name folder) "current"))
            :on {:click #(choose-folder! name)}}
       [:span (str/capitalize (str/replace name "-" " "))]
       [:span (if (pos? unread) [:span.count (str unread)] [:span.muted-flag (str total)])]])]
   [:h2 "Contacts"]
   [:ul.contacts
    (for [{:keys [address name online]} contacts]
      [:li {:replicant/key address
            :title (str "Waves with " name)
            :on {:click #(search! (str "with:" name))}}
       [:span {:class (classes "dot" (when online "online"))}]
       (avatar address "avatar small")
       [:span name]])]])

(defn wave-row-view [{:keys [open-id]} {:keys [id title snippet participants last_modified
                                                blip_count unread_count muted]}]
  [:li {:replicant/key id
        :class (classes "wave-row"
                        (when (pos? unread_count) "unread")
                        (when (= id open-id) "selected"))
        :data-wave-id id
        :on {:click #(open-wave! id)}}
   [:span.avatars
    (for [{:keys [address]} (take 3 participants)]
      [:span {:replicant/key address} (avatar address)])]
   [:span.summary
    [:b (if (str/blank? title) "(untitled)" title)]
    (when (seq snippet) [:span.snippet (str " — " snippet)])]
   [:span.meta
    (when (pos? unread_count) [:span.badge (str unread_count)])
    " " (short-time last_modified)
    [:br]
    (str blip_count (if (= 1 blip_count) " msg" " msgs"))
    (when muted [:span.muted-flag " muted"])]])

(defn wave-list-view [{:keys [waves folder] :as current}]
  [:section.pane
   [:div.list-tools
    [:input (merge {:type "search" :placeholder "Search: text is:unread with:bob tag:x"}
                   (bind :query)
                   {:on {:input (fn [event] (swap! state assoc :query (.. event -target -value)))
                         :keydown (on-enter load-list!)}})]
    [:button {:on {:click load-list!}} "Search"]]
   [:div.list-tools
    [:input (merge {:placeholder "New wave title"}
                   (bind :new-title)
                   {:on {:input (fn [event] (swap! state assoc :new-title (.. event -target -value)))
                         :keydown (on-enter create-wave!)}})]
    [:button.primary {:on {:click create-wave!}} "New wave"]]
   [:h2 (str (str/capitalize (str/replace folder "-" " ")) " · " (count waves))]
   (if (seq waves)
     [:ul.wave-list (for [summary waves] (wave-row-view current summary))]
     [:p.empty "No waves here."])])

(defn gadget-view [me {:keys [id title votes]}]
  (let [my-address (:address me)]
    [:table.gadget {:replicant/key id :data-gadget-id id}
     [:caption (if (str/blank? title) "Yes / No / Maybe" title)]
     [:thead
      [:tr (for [choice gadget-choices]
             [:th {:replicant/key choice}
              (str (str/capitalize choice) " (" (count (get votes (keyword choice))) ")")])]]
     [:tbody
      [:tr (for [choice gadget-choices]
             [:td {:replicant/key choice}
              (for [voter (get votes (keyword choice))]
                [:span {:replicant/key voter} (avatar voter "avatar small")])])]
      [:tr (for [choice gadget-choices]
             (let [mine (some #{my-address} (get votes (keyword choice)))]
               [:td {:replicant/key choice}
                [:button {:class (classes "vote" (when mine "chosen"))
                          :data-choice choice
                          :on {:click #(vote! id choice)}}
                 (str/capitalize choice)]]))]]]))

(defn reply-box-view [parent-id text-key placeholder]
  [:div.reply-box
   [:textarea (merge {:placeholder placeholder} (bind text-key))]
   [:div
    [:button.primary {:on {:click #(post-reply! parent-id text-key)}} "Send"]
    (when parent-id
      [:button {:on {:click #(swap! state assoc :reply-parent nil :reply-text "")}} "Cancel"])]])

(defn blip-view [{:keys [me reply-parent] :as current} {:keys [id author created lines unread gadgets children]}]
  [:div {:replicant/key id
         :class (classes "blip" (when unread "unread"))
         :data-blip-id id}
   [:div.blip-head (avatar author "avatar small") [:b (local-name author)] [:span (short-time created)]]
   [:div.blip-body (map-indexed (fn [index line] [:p {:replicant/key index} line]) lines)]
   (for [gadget gadgets] (gadget-view me gadget))
   [:div.blip-actions
    [:button {:on {:click #(swap! state assoc :reply-parent id :reply-text "")}} "Reply"]]
   (when (= reply-parent id)
     (reply-box-view id :reply-text (str "Reply to " (local-name author))))
   (when (seq children)
     [:div.thread (for [child children] (blip-view current child))])])

(defn open-wave-view [{:keys [open-id open-wave] :as current}]
  (cond
    (nil? open-id) [:section.pane [:p.empty "Select a wave."]]
    (nil? open-wave) [:section.pane [:p.empty "Loading…"]]
    :else
    (let [{:keys [title participants public tags blips muted archived]} open-wave]
      [:section.pane.open-wave
       [:div.wave-header
        [:h2 (if (str/blank? title) "(untitled)" title)]
        [:div.participants
         (for [{:keys [address]} participants]
           [:span {:replicant/key address} (avatar address)])
         [:span.inline-form
          [:input (merge {:placeholder "add participant"} (bind :participant-text)
                         {:on {:input (fn [event] (swap! state assoc :participant-text (.. event -target -value)))
                               :keydown (on-enter add-participant!)}})]
          [:button {:on {:click add-participant!}} "+"]]]
        [:div.toolbar
         (for [[action label] wave-actions]
           [:button {:replicant/key action :data-action action :on {:click #(wave-action! action)}} label])]
        (when (or muted archived)
          [:div.muted-flag (str/join ", " (remove nil? [(when muted "muted") (when archived "archived")]))])]
       (when public
         [:div.banner "Everyone has access to this wave (public)."])
       [:div.tags
        [:span.muted-flag "Tags:"]
        (for [tag tags]
          [:span.tag {:replicant/key tag} tag
           [:button {:title (str "Remove " tag) :on {:click #(change-tags! {:remove [tag]})}} "×"]])
        [:span.inline-form
         [:input (merge {:placeholder "add tag"} (bind :tag-text)
                        {:on {:input (fn [event] (swap! state assoc :tag-text (.. event -target -value)))
                              :keydown (on-enter #(change-tags! {:add [(str/trim (:tag-text @state))]}))}})]
         [:button {:on {:click #(change-tags! {:add [(str/trim (:tag-text @state))]})}} "+"]]]
       [:div.blips
        (for [blip blips] (blip-view current blip))
        (reply-box-view nil :wave-reply-text "Click here to reply to the wave")]])))

(defn app-view [current]
  [:div
   (topbar-view current)
   (when-let [message (:error current)]
     [:div.error message " " [:button {:on {:click clear-error!}} "dismiss"]])
   [:main.panes
    (navigation-view current)
    (wave-list-view current)
    (open-wave-view current)]])

;; ------------------------------------------------------------------ boot

(def root-element (.getElementById js/document "root"))

(defn render! [] (replicant/render root-element (app-view @state)))

(add-watch state ::render (fn [_ _ _ _] (render!)))

(render!)
(load-avatars!)
(load-me!)
(load-contacts!)
(refresh!)
(defonce poller (js/setInterval (fn [] (load-contacts!) (refresh!)) poll-interval-ms))
