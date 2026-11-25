;; /admin: server overview, run in the page by scittle.
;;
;; Version and health, stats, users, waves; clicking a wave shows its raw
;; wavelets from /api/admin/waves/{id}. The browser resends the Basic
;; credentials it was given for /admin (realm wave-admin) on these same-origin
;; fetches, so this file never sees a password.

(ns wave.admin
  (:require [clojure.string :as str]
            [replicant.dom :as replicant]))

(def poll-interval-ms 10000)

(defonce state
  (atom {:health nil
         :stats nil
         :users []
         :waves []
         :selected-id nil
         :raw-json nil
         :error nil}))

(defn api-url
  "Absolute same-origin URL; location.origin never carries userinfo."
  [path]
  (str (.-origin js/location) path))

(defn fetch-json
  "Resolves to the parsed JS value, untouched, so raw JSON can be shown as-is."
  [path]
  (-> (js/fetch (api-url path) #js {:credentials "same-origin" :headers #js {"Accept" "application/json"}})
      (.then (fn [response]
               (if (.-ok response)
                 (.json response)
                 (throw (js/Error. (str "GET " path " failed: " (.-status response)))))))))

(defn fetch-clj [path]
  (.then (fetch-json path) #(js->clj % :keywordize-keys true)))

(defn show-error! [error] (swap! state assoc :error (.-message error)))

(defn load-raw-wave! [wave-id]
  (swap! state assoc :selected-id wave-id :raw-json nil)
  (-> (fetch-json (str "/api/admin/waves/" (js/encodeURIComponent wave-id)))
      (.then #(swap! state assoc :raw-json (.stringify js/JSON % nil 2)))
      (.catch show-error!)))

(defn refresh! []
  (-> (fetch-clj "/health") (.then #(swap! state assoc :health %)) (.catch show-error!))
  (-> (fetch-clj "/api/admin/stats") (.then #(swap! state assoc :stats %)) (.catch show-error!))
  (-> (fetch-clj "/api/admin/users") (.then #(swap! state assoc :users %)) (.catch show-error!))
  (-> (fetch-clj "/api/admin/waves") (.then #(swap! state assoc :waves %)) (.catch show-error!)))

(defn local-name [address] (first (str/split (or address "") #"@")))

(defn short-time [iso-text]
  (when iso-text
    (let [moment (js/Date. (if (re-find #"(Z|[+-]\d\d:\d\d)$" iso-text) iso-text (str iso-text "Z")))]
      (.toLocaleString moment js/undefined #js {:month "short" :day "numeric" :hour "numeric" :minute "2-digit"}))))

(defn stat-view [label value]
  [:div.stat {:replicant/key label} [:b (str value)] [:span label]])

(defn stats-view [{:keys [health stats]}]
  [:section.pane.wide
   [:h2 "Server"]
   [:div.stats
    (stat-view "version" (or (:version stats) "…"))
    [:div.stat {:replicant/key "health"}
     [:b {:class (when (= "healthy" (:status health)) "ok")} (or (:status health) "…")]
     [:span "health"]]
    (stat-view "waves" (:waves stats))
    (stat-view "wavelets" (:wavelets stats))
    (stat-view "users" (:users stats))
    (stat-view "open connections" (reduce + 0 (vals (:connections stats))))]])

(defn users-view [{:keys [users]}]
  [:section.pane
   [:h2 (str "Users · " (count users))]
   [:table.data
    [:thead [:tr [:th "address"] [:th "waves"] [:th "created"] [:th "online"]]]
    [:tbody
     (for [{:keys [address waves created online]} users]
       [:tr {:replicant/key address}
        [:td address] [:td (str waves)] [:td (str created)]
        [:td [:span {:class (if online "dot online" "dot")}]]])]]])

(defn waves-view [{:keys [waves selected-id]}]
  [:section.pane
   [:h2 (str "Waves · " (count waves))]
   [:table.data
    [:thead [:tr [:th "title"] [:th "creator"] [:th "participants"] [:th "blips"] [:th "last modified"]]]
    [:tbody
     (for [{:keys [id title creator participants blip_count last_modified]} waves]
       [:tr {:replicant/key id
             :class (if (= id selected-id) ["clickable" "selected"] ["clickable"])
             :data-wave-id id
             :title id
             :on {:click #(load-raw-wave! id)}}
        [:td.title (if (str/blank? title) "(untitled)" title)]
        [:td (local-name creator)]
        [:td (str (count participants))]
        [:td (str blip_count)]
        [:td (short-time last_modified)]])]]])

(defn raw-view [{:keys [selected-id raw-json]}]
  [:section.pane.wide
   [:h2 (if selected-id (str "Raw wavelets · " selected-id) "Raw wavelets")]
   (cond
     (nil? selected-id) [:p.empty "Click a wave to see its wavelets."]
     (nil? raw-json) [:p.empty "Loading…"]
     :else [:pre.raw raw-json])])

(defn admin-view [current]
  [:div
   [:header.topbar [:h1 "Wave Admin"] [:span.spacer] [:a {:href "/app"} "Wave"] [:a {:href "/logout"} "Sign out"]]
   (when-let [message (:error current)]
     [:div.error message " " [:button {:on {:click #(swap! state assoc :error nil)}} "dismiss"]])
   [:main.admin-grid
    (stats-view current)
    (users-view current)
    (waves-view current)
    (raw-view current)]])

(def root-element (.getElementById js/document "root"))

(defn render! [] (replicant/render root-element (admin-view @state)))

(add-watch state ::render (fn [_ _ _ _] (render!)))

(render!)
(refresh!)
(defonce poller (js/setInterval refresh! poll-interval-ms))
